import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.core.enums import DocumentStatus
from app.knowledge.model import Knowledge, Document

logger = logging.getLogger("supportai.knowledge.repository")


class KnowledgeRepository:
    """
    Data-access layer for the 'knowledge' collection in MongoDB.
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None) -> None:
        self._db = db

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._db or get_database()

    async def create(self, knowledge: Knowledge) -> Knowledge:
        """
        Persists a new knowledge source.
        """
        payload = knowledge.to_mongo()
        await self.db["knowledge"].insert_one(payload)
        return knowledge

    async def get_by_id(self, knowledge_id: UUID, include_deleted: bool = False) -> Optional[Knowledge]:
        """
        Retrieves a knowledge source by ID.
        """
        query: Dict[str, Any] = {"knowledge_id": knowledge_id}
        if not include_deleted:
            query["is_deleted"] = False
        data = await self.db["knowledge"].find_one(query)
        return Knowledge.from_mongo(data) if data else None

    async def list_by_company(self, company_id: UUID, include_deleted: bool = False) -> List[Knowledge]:
        """
        Lists all knowledge sources for a company.
        """
        query: Dict[str, Any] = {"company_id": company_id}
        if not include_deleted:
            query["is_deleted"] = False
        cursor = self.db["knowledge"].find(query).sort("created_at", -1)
        raw_results = await cursor.to_list(length=100)
        results = []
        for r in raw_results:
            k = Knowledge.from_mongo(r)
            if k:
                results.append(k)
        return results

    async def update(self, knowledge: Knowledge) -> Optional[Knowledge]:
        """
        Updates a knowledge source using optimistic concurrency version control.
        """
        payload = knowledge.to_mongo()
        payload.pop("_id", None)

        current_version = knowledge.version or 1
        payload["version"] = current_version + 1
        knowledge.update_audit(knowledge.updated_by)
        payload["updated_at"] = knowledge.updated_at

        result = await self.db["knowledge"].replace_one(
            {"knowledge_id": knowledge.knowledge_id, "version": current_version},
            payload
        )

        if result.modified_count == 0:
            return None

        knowledge.version = current_version + 1
        return knowledge

    async def soft_delete(self, knowledge_id: UUID, modifier_id: UUID) -> bool:
        """
        Flags a knowledge source as soft-deleted.
        """
        now = datetime.now(timezone.utc)
        result = await self.db["knowledge"].update_one(
            {"knowledge_id": knowledge_id, "is_deleted": False},
            {
                "$set": {
                    "is_deleted": True,
                    "deleted_at": now,
                    "status": DocumentStatus.ARCHIVED.value,
                    "updated_at": now,
                    "updated_by": modifier_id
                }
            }
        )
        return result.modified_count > 0


class DocumentRepository:
    """
    Data-access layer for the 'documents' collection (storing text chunks and embeddings).
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None) -> None:
        self._db = db

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._db or get_database()

    async def create(self, doc: Document) -> Document:
        """
        Persists a text chunk.
        """
        payload = doc.to_mongo()
        await self.db["documents"].insert_one(payload)
        return doc

    async def get_chunks(self, knowledge_id: UUID, version: int, include_deleted: bool = False) -> List[Document]:
        """
        Retrieves all chunks matching a knowledge ID and version, sorted by chunk index.
        """
        query: Dict[str, Any] = {
            "knowledge_id": knowledge_id,
            "metadata.version": version if version is not None else {"$exists": True}
        }
        if not include_deleted:
            query["is_deleted"] = False
        cursor = self.db["documents"].find(query).sort("chunk_index", 1)
        raw_results = await cursor.to_list(length=1000)
        results = []
        for r in raw_results:
            d = Document.from_mongo(r)
            if d:
                results.append(d)
        return results

    async def soft_delete_chunks_by_version(self, knowledge_id: UUID, version: int, modifier_id: UUID) -> int:
        """
        Soft-deletes all chunks of a specific version for a knowledge source.
        """
        now = datetime.now(timezone.utc)
        result = await self.db["documents"].update_many(
            {"knowledge_id": knowledge_id, "metadata.version": version, "is_deleted": False},
            {
                "$set": {
                    "is_deleted": True,
                    "deleted_at": now,
                    "updated_at": now,
                    "updated_by": modifier_id
                }
            }
        )
        return result.modified_count

    async def vector_search(
        self,
        company_id: UUID,
        query_vector: List[float],
        limit: int = 5,
        min_score: float = 0.0
    ) -> List[dict]:
        """
        Performs vector cosine similarity search using MongoDB Atlas Vector Search,
        with an in-memory cosine similarity fallback for local development/testing.
        """
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_embedding",
                    "path": "vector_embedding",
                    "queryVector": query_vector,
                    "numCandidates": limit * 10,
                    "limit": limit,
                    "filter": {
                        "company_id": str(company_id),
                        "is_deleted": False
                    }
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "document_id": 1,
                    "parent_document_id": 1,
                    "knowledge_id": 1,
                    "company_id": 1,
                    "chunk_index": 1,
                    "content": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]

        try:
            cursor = self.db["documents"].aggregate(pipeline)
            results = await cursor.to_list(length=limit)
            return results
        except Exception as e:
            logger.warning(f"MongoDB Atlas Vector Search query failed ({e}). Falling back to in-memory evaluation...")
            # Query all non-deleted documents for the company
            find_cursor = self.db["documents"].find({
                "company_id": company_id,
                "is_deleted": False
            })
            raw_docs = await find_cursor.to_list(length=2000)

            import math
            def cosine_similarity(v1, v2):
                if not v1 or not v2:
                    return 0.0
                dot_product = sum(a * b for a, b in zip(v1, v2))
                magnitude1 = math.sqrt(sum(a * a for a in v1))
                magnitude2 = math.sqrt(sum(b * b for b in v2))
                if magnitude1 * magnitude2 == 0:
                    return 0.0
                return dot_product / (magnitude1 * magnitude2)

            scored = []
            for doc in raw_docs:
                v = doc.get("vector_embedding")
                if v:
                    score = cosine_similarity(query_vector, v)
                    if score >= min_score:
                        d = Document.from_mongo(doc)
                        if d:
                            item = d.model_dump()
                            item.pop("vector_embedding", None)
                            item["score"] = score
                            scored.append(item)

            scored.sort(key=lambda x: x["score"], reverse=True)
            return scored[:limit]
