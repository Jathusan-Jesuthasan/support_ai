import os
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID
from fastapi import UploadFile

from app.core.enums import DocumentStatus
from app.shared.exceptions import NotFoundException, BadRequestException, ConflictException
from app.knowledge.model import Knowledge
from app.knowledge.repository import KnowledgeRepository, DocumentRepository

logger = logging.getLogger("supportai.knowledge.service")


class KnowledgeService:
    """
    Coordinates document ingestion pipelines, text parsing, semantic chunking, and search indexing.
    """

    def __init__(
        self,
        knowledge_repo: Optional[KnowledgeRepository] = None,
        document_repo: Optional[DocumentRepository] = None,
        upload_dir: str = "uploads"
    ) -> None:
        self.knowledge_repo = knowledge_repo or KnowledgeRepository()
        self.document_repo = document_repo or DocumentRepository()
        self.upload_dir = upload_dir
        os.makedirs(self.upload_dir, exist_ok=True)

    async def create_knowledge(
        self,
        company_id: UUID,
        name: str,
        description: Optional[str],
        source_type: str,
        creator_id: UUID
    ) -> Knowledge:
        """
        Registers a new knowledge source.
        """
        now = datetime.now(timezone.utc)
        k = Knowledge(
            knowledge_id=uuid.uuid4(),
            company_id=company_id,
            name=name,
            description=description,
            source_type=source_type,
            status=DocumentStatus.UPLOADED,
            current_version=1,
            created_by=creator_id,
            updated_by=creator_id,
            created_at=now,
            updated_at=now
        )
        return await self.knowledge_repo.create(k)

    async def upload_document_file(
        self,
        company_id: UUID,
        knowledge_id: UUID,
        file: UploadFile,
        creator_id: UUID
    ) -> Knowledge:
        """
        Saves uploaded file binary locally and triggers background parsing/vectorizing task.
        """
        k = await self.knowledge_repo.get_by_id(knowledge_id)
        if not k or k.company_id != company_id:
            raise NotFoundException("Knowledge source not found")

        # Validate file constraints
        # Max size: 10MB
        file_bytes = await file.read()
        if len(file_bytes) > 10 * 1024 * 1024:
            raise BadRequestException("File size exceeds the 10MB limit")

        filename = file.filename or "uploaded_file"
        file_ext = os.path.splitext(filename)[1].lower().strip(".")
        allowed_exts = {"pdf", "txt", "md", "docx"}
        if file_ext not in allowed_exts:
            raise BadRequestException(f"Unsupported file extension: {file_ext}. Allowed: PDF, TXT, MD, DOCX")

        # Save to local upload directory
        file_uuid = uuid.uuid4()
        dest_filename = f"{company_id}_{file_uuid}_{filename}"
        dest_path = os.path.join(self.upload_dir, dest_filename)
        with open(dest_path, "wb") as f:
            f.write(file_bytes)

        # Update knowledge status
        k.status = DocumentStatus.PROCESSING
        k.file_url = dest_path
        k.updated_by = creator_id
        await self.knowledge_repo.update(k)

        # Trigger Celery background task
        # Import task locally to avoid circular dependencies
        from app.knowledge.tasks import process_document_task
        process_document_task.delay(
            str(company_id),
            str(knowledge_id),
            dest_path,
            filename,
            str(creator_id)
        )

        return k

    def extract_text_and_pages(self, file_path: str) -> List[Tuple[Optional[int], str]]:
        """
        Extracts pages of text from file. Returns a list of (page_number, text) tuples.
        """
        ext = os.path.splitext(file_path)[1].lower().strip(".")
        pages_content: List[Tuple[Optional[int], str]] = []

        if ext == "pdf":
            import pypdf
            reader = pypdf.PdfReader(file_path)
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages_content.append((idx + 1, text))
        elif ext == "docx":
            import docx
            doc = docx.Document(file_path)
            # Combine paragraphs into a single page context (page = None)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            full_text = "\n\n".join(paragraphs)
            pages_content.append((None, full_text))
        else:
            # txt, md
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            pages_content.append((None, content))

        return pages_content

    def chunk_text(
        self,
        pages_content: List[Tuple[Optional[int], str]],
        chunk_size: int = 600,
        overlap: int = 120
    ) -> List[Tuple[Optional[int], str]]:
        """
        Chunks text with slide overlapping window.
        Returns list of (page_number, chunk_text) tuples.
        """
        chunks: List[Tuple[Optional[int], str]] = []
        for page_num, text in pages_content:
            text = text.strip()
            if not text:
                continue

            # Check if sliding window character splitter is needed
            if len(text) <= chunk_size:
                chunks.append((page_num, text))
                continue

            start = 0
            while start < len(text):
                end = start + chunk_size
                chunk = text[start:end].strip()
                if chunk:
                    chunks.append((page_num, chunk))
                start += (chunk_size - overlap)
        return chunks

    async def get_knowledge(self, company_id: UUID, knowledge_id: UUID) -> Knowledge:
        """
        Retrieves a knowledge source by ID.
        """
        k = await self.knowledge_repo.get_by_id(knowledge_id)
        if not k or k.company_id != company_id:
            raise NotFoundException("Knowledge source not found")
        return k

    async def list_knowledge(self, company_id: UUID) -> List[Knowledge]:
        """
        Lists all knowledge sources for a company.
        """
        return await self.knowledge_repo.list_by_company(company_id)

    async def delete_knowledge(self, company_id: UUID, knowledge_id: UUID, modifier_id: UUID) -> None:
        """
        Logically deletes a knowledge source and all its related text chunks.
        """
        k = await self.knowledge_repo.get_by_id(knowledge_id)
        if not k or k.company_id != company_id:
            raise NotFoundException("Knowledge source not found")

        # Soft delete the knowledge metadata
        success = await self.knowledge_repo.soft_delete(knowledge_id, modifier_id)
        if not success:
            raise ConflictException("Failed to delete knowledge source")

        # Soft delete all document chunks in current version
        await self.document_repo.soft_delete_chunks_by_version(
            knowledge_id=knowledge_id,
            version=k.current_version,
            modifier_id=modifier_id
        )
