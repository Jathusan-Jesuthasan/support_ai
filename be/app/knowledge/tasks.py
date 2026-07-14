import asyncio
from uuid import UUID
from celery.utils.log import get_task_logger

from app.worker import celery_app
from app.core.enums import DocumentStatus
from app.core.database import db_manager
from app.knowledge.model import Document, ChunkMetadata
from app.knowledge.repository import KnowledgeRepository, DocumentRepository
from app.knowledge.service import KnowledgeService
from app.ai.service import AIService, generate_mock_embedding

logger = get_task_logger("supportai.knowledge.tasks")


async def _process_document(
    company_id: str,
    knowledge_id: str,
    file_path: str,
    filename: str,
    creator_id: str
):
    # Initialize DB connection for the worker process
    await db_manager.connect()
    try:
        k_repo = KnowledgeRepository()
        d_repo = DocumentRepository()
        k_service = KnowledgeService(k_repo, d_repo)
        ai_service = AIService()

        comp_uuid = UUID(company_id)
        know_uuid = UUID(knowledge_id)
        user_uuid = UUID(creator_id)

        # 1. Retrieve Knowledge source record
        k = await k_repo.get_by_id(know_uuid)
        if not k:
            logger.error(f"Knowledge record {knowledge_id} not found.")
            return

        # 2. Extract Pages
        logger.info(f"Extracting text from {file_path}")
        pages = k_service.extract_text_and_pages(file_path)
        
        # 3. Chunk text
        chunks = k_service.chunk_text(pages)
        if not chunks:
            logger.warning(f"No text extracted or chunked from file: {filename}")
            k.status = DocumentStatus.FAILED
            await k_repo.update(k)
            return

        # 4. Generate new version chunks in status processing/indexed
        new_version = k.current_version + 1 if k.file_url else k.current_version
        
        # Attempt AI metadata tags and summary extraction
        # Combine first few chunks for summarizing document context
        sample_text = "\n".join([chunk_text for _, chunk_text in chunks[:3]])
        try:
            summary = await ai_service.generate_document_summary(sample_text)
            tags = await ai_service.extract_tags(sample_text)
        except Exception as e:
            logger.warning(f"AI summary/tag extraction failed: {e}. Using empty defaults.")
            summary = "Automatic chunk extraction"
            tags = ["general"]

        logger.info(f"Generating vectors for {len(chunks)} chunks under version {new_version}")

        # Vectorize and save chunks
        for idx, (page_num, chunk_text) in enumerate(chunks):
            # Generate embedding vector
            try:
                embedding = await ai_service.generate_embeddings([chunk_text])
                vector = embedding[0]
            except Exception as e:
                logger.warning(f"Embedding generation via LLM API failed ({e}). Falling back to mock embeddings...")
                vector = generate_mock_embedding(chunk_text)

            chunk_id = UUID(int=hash(f"{knowledge_id}_{new_version}_{idx}") & ((1 << 128) - 1))
            metadata = ChunkMetadata(
                source_title=filename,
                file_type=filename.split(".")[-1].upper(),
                summary=summary,
                tags=tags,
                page_number=page_num,
                section=f"Section {idx + 1}",
                language="en",
                embedding_model="text-embedding-004",
                version=new_version
            )

            doc_chunk = Document(
                document_id=chunk_id,
                parent_document_id=know_uuid,
                knowledge_id=know_uuid,
                company_id=comp_uuid,
                chunk_index=idx,
                chunk_order=idx,
                content=chunk_text,
                vector_embedding=vector,
                metadata=metadata,
                created_by=user_uuid,
                updated_by=user_uuid
            )
            # Persist chunk
            await d_repo.create(doc_chunk)

        # 5. Atomic Promotion
        old_version = k.current_version
        k.current_version = new_version
        k.status = DocumentStatus.INDEXED
        k.updated_by = user_uuid
        await k_repo.update(k)

        # 6. Cleanup old chunks (if version upgraded)
        if new_version > old_version:
            logger.info(f"Archiving old chunks of version {old_version}")
            await d_repo.soft_delete_chunks_by_version(know_uuid, old_version, user_uuid)

        logger.info(f"Ingestion successful for document: {filename}. Status: INDEXED")

    except Exception as exc:
        logger.error(f"Failed to process document {filename}: {exc}", exc_info=True)
        # Attempt to set knowledge status to FAILED
        try:
            k = await k_repo.get_by_id(UUID(knowledge_id))
            if k:
                k.status = DocumentStatus.FAILED
                await k_repo.update(k)
        except Exception as db_err:
            logger.critical(f"Failed to write failure status to DB: {db_err}")
    finally:
        db_manager.disconnect()


@celery_app.task(name="app.knowledge.tasks.process_document_task")
def process_document_task(
    company_id: str,
    knowledge_id: str,
    file_path: str,
    filename: str,
    creator_id: str
):
    """
    Celery task running the async extraction and embedding loops inside a synchronous thread context.
    """
    import concurrent.futures
    
    coro = _process_document(
        company_id=company_id,
        knowledge_id=knowledge_id,
        file_path=file_path,
        filename=filename,
        creator_id=creator_id
    )

    def run_in_new_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_in_new_loop)
        return future.result()
