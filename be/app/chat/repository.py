import base64
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.chat.model import Conversation, Message, Product

logger = logging.getLogger("supportai.chat.repository")


def encode_cursor(timestamp_val: datetime, uuid_val: UUID) -> str:
    """
    Encodes sorting fields into a base64 URL-safe cursor string.
    """
    data = {"t": timestamp_val.isoformat(), "id": str(uuid_val)}
    js_str = json.dumps(data)
    return base64.urlsafe_b64encode(js_str.encode("utf-8")).decode("utf-8")


def decode_cursor(cursor_str: str) -> Optional[Dict[str, Any]]:
    """
    Decodes a base64 cursor back into its raw dict fields.
    """
    try:
        decoded = base64.urlsafe_b64decode(cursor_str.encode("utf-8")).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        return None


class ConversationRepository:
    """
    Handles MongoDB persistence for conversation widget sessions.
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None) -> None:
        self._db = db

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._db or get_database()

    async def get_by_id(self, conversation_id: UUID, include_deleted: bool = False) -> Optional[Conversation]:
        query: Dict[str, Any] = {"conversation_id": conversation_id}
        if not include_deleted:
            query["is_deleted"] = False
        data = await self.db["conversations"].find_one(query)
        return Conversation.from_mongo(data) if data else None

    async def create(self, conv: Conversation) -> Conversation:
        payload = conv.to_mongo()
        await self.db["conversations"].insert_one(payload)
        return conv

    async def update(self, conv: Conversation) -> Optional[Conversation]:
        payload = conv.to_mongo()
        payload.pop("_id", None)
        result = await self.db["conversations"].replace_one(
            {"conversation_id": conv.conversation_id},
            payload
        )
        return conv if result.modified_count > 0 or result.matched_count > 0 else None

    async def list_conversations(
        self,
        company_id: UUID,
        limit: int = 20,
        cursor: Optional[str] = None
    ) -> Tuple[List[Conversation], Optional[str], bool]:
        """
        Retrieves a cursor-paginated list of active conversations, ordered by last_message_at DESC.
        """
        query: Dict[str, Any] = {
            "company_id": company_id,
            "is_deleted": False
        }

        if cursor:
            c_data = decode_cursor(cursor)
            if c_data:
                c_time = datetime.fromisoformat(c_data["t"])
                c_id = UUID(c_data["id"])
                # Return items older than the cursor, or equal but tie-broken by UUID
                query["$or"] = [
                    {"last_message_at": {"$lt": c_time}},
                    {"last_message_at": c_time, "conversation_id": {"$lt": c_id}}
                ]

        # Fetch limit + 1 to check if there are more pages
        cursor_obj = self.db["conversations"].find(query).sort([
            ("last_message_at", -1),
            ("conversation_id", -1)
        ]).limit(limit + 1)

        raw_docs = await cursor_obj.to_list(length=limit + 1)
        
        has_more = len(raw_docs) > limit
        
        items: List[Conversation] = []
        for doc in raw_docs[:limit]:
            c = Conversation.from_mongo(doc)
            if c:
                items.append(c)

        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            next_cursor = encode_cursor(last_item.last_message_at, last_item.conversation_id)

        return items, next_cursor, has_more


class MessageRepository:
    """
    Handles MongoDB persistence for conversation log messages.
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None) -> None:
        self._db = db

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._db or get_database()

    async def get_by_id(self, message_id: UUID) -> Optional[Message]:
        data = await self.db["messages"].find_one({"message_id": message_id, "is_deleted": False})
        return Message.from_mongo(data) if data else None

    async def create(self, msg: Message) -> Message:
        payload = msg.to_mongo()
        await self.db["messages"].insert_one(payload)
        return msg

    async def update(self, msg: Message) -> Optional[Message]:
        payload = msg.to_mongo()
        payload.pop("_id", None)
        result = await self.db["messages"].replace_one(
            {"message_id": msg.message_id},
            payload
        )
        return msg if result.modified_count > 0 or result.matched_count > 0 else None

    async def list_messages(
        self,
        conversation_id: UUID,
        limit: int = 50,
        cursor: Optional[str] = None
    ) -> Tuple[List[Message], Optional[str], bool]:
        """
        Retrieves a cursor-paginated list of messages for a conversation, ordered by created_at DESC.
        """
        query: Dict[str, Any] = {
            "conversation_id": conversation_id,
            "is_deleted": False
        }

        if cursor:
            c_data = decode_cursor(cursor)
            if c_data:
                c_time = datetime.fromisoformat(c_data["t"])
                c_id = UUID(c_data["id"])
                query["$or"] = [
                    {"created_at": {"$lt": c_time}},
                    {"created_at": c_time, "message_id": {"$lt": c_id}}
                ]

        cursor_obj = self.db["messages"].find(query).sort([
            ("created_at", -1),
            ("message_id", -1)
        ]).limit(limit + 1)

        raw_docs = await cursor_obj.to_list(length=limit + 1)
        
        has_more = len(raw_docs) > limit
        
        items: List[Message] = []
        for doc in raw_docs[:limit]:
            m = Message.from_mongo(doc)
            if m:
                items.append(m)

        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            next_cursor = encode_cursor(last_item.created_at, last_item.message_id)

        return items, next_cursor, has_more

    async def get_recent_history(self, conversation_id: UUID, limit: int = 6) -> List[Message]:
        """
        Fetches the last N messages in chronological order (created_at ASC) for LLM context assembly.
        """
        cursor_obj = self.db["messages"].find({
            "conversation_id": conversation_id,
            "is_deleted": False
        }).sort("created_at", -1).limit(limit)

        raw_docs = await cursor_obj.to_list(length=limit)
        
        items: List[Message] = []
        for doc in raw_docs:
            m = Message.from_mongo(doc)
            if m:
                items.append(m)
                
        items.reverse()  # Chronological order
        return items


class ProductRepository:
    """
    Handles MongoDB persistence for tenant catalog items.
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None) -> None:
        self._db = db

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._db or get_database()

    async def get_by_id(self, product_id: UUID) -> Optional[Product]:
        data = await self.db["products"].find_one({"product_id": product_id, "is_deleted": False})
        return Product.from_mongo(data) if data else None

    async def get_by_sku(self, company_id: UUID, sku: str) -> Optional[Product]:
        data = await self.db["products"].find_one({
            "company_id": company_id,
            "sku": sku,
            "is_deleted": False
        })
        return Product.from_mongo(data) if data else None

    async def create(self, prod: Product) -> Product:
        payload = prod.to_mongo()
        await self.db["products"].insert_one(payload)
        return prod

    async def update(self, prod: Product) -> Optional[Product]:
        payload = prod.to_mongo()
        payload.pop("_id", None)
        result = await self.db["products"].replace_one(
            {"product_id": prod.product_id},
            payload
        )
        return prod if result.modified_count > 0 or result.matched_count > 0 else None

    async def list_products(self, company_id: UUID, limit: int = 100) -> List[Product]:
        cursor_obj = self.db["products"].find({
            "company_id": company_id,
            "is_deleted": False
        }).limit(limit)
        raw_docs = await cursor_obj.to_list(length=limit)
        
        items: List[Product] = []
        for doc in raw_docs:
            p = Product.from_mongo(doc)
            if p:
                items.append(p)
        return items

    async def text_search(self, company_id: UUID, query: str, limit: int = 5) -> List[Product]:
        """
        Performs a text search on the products catalog. Falls back to regex if text index fails.
        """
        # Try full text search first
        try:
            cursor_obj = self.db["products"].find(
                {
                    "company_id": company_id,
                    "is_deleted": False,
                    "$text": {"$search": query}
                },
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            raw_docs = await cursor_obj.to_list(length=limit)
            if raw_docs:
                items: List[Product] = []
                for doc in raw_docs:
                    p = Product.from_mongo(doc)
                    if p:
                        items.append(p)
                return items
        except Exception:
            logger.warning("MongoDB text search query failed. Falling back to regex query...")

        # Fallback regex search
        cursor_obj = self.db["products"].find({
            "company_id": company_id,
            "is_deleted": False,
            "$or": [
                {"name": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}},
                {"sku": {"$regex": query, "$options": "i"}}
            ]
        }).limit(limit)
        raw_docs = await cursor_obj.to_list(length=limit)
        
        items = []
        for doc in raw_docs:
            p = Product.from_mongo(doc)
            if p:
                items.append(p)
        return items
