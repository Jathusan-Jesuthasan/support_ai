import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.enums import ConversationStatus, SenderType
from app.shared.exceptions import NotFoundException, ConflictException, DuplicateResourceException
from app.company.repository import CompanyRepository
from app.knowledge.repository import DocumentRepository
from app.ai.service import AIService
from app.chat.model import Conversation, Message, Citation, Product
from app.chat.repository import ConversationRepository, MessageRepository, ProductRepository

logger = logging.getLogger("supportai.chat.service")


class ChatService:
    """
    Coordinates chat messaging sessions, RAG retrieval, generative completion, and agent escalations.
    """

    def __init__(
        self,
        conversation_repo: Optional[ConversationRepository] = None,
        message_repo: Optional[MessageRepository] = None,
        product_repo: Optional[ProductRepository] = None,
        company_repo: Optional[CompanyRepository] = None,
        document_repo: Optional[DocumentRepository] = None,
        ai_service: Optional[AIService] = None
    ) -> None:
        self.conversation_repo = conversation_repo or ConversationRepository()
        self.message_repo = message_repo or MessageRepository()
        self.product_repo = product_repo or ProductRepository()
        self.company_repo = company_repo or CompanyRepository()
        self.document_repo = document_repo or DocumentRepository()
        self.ai_service = ai_service or AIService()

    async def create_conversation(
        self,
        company_id: UUID,
        user_identifier: Optional[str] = None
    ) -> Conversation:
        """
        Initializes a new customer widget conversation session.
        """
        company = await self.company_repo.get_by_company_id(company_id)
        if not company:
            raise NotFoundException("Company workspace not found")

        now = datetime.now(timezone.utc)
        conv = Conversation(
            conversation_id=uuid.uuid4(),
            company_id=company_id,
            user_identifier=user_identifier or f"guest_{uuid.uuid4().hex[:12]}",
            status=ConversationStatus.OPEN,
            last_message_at=now
        )
        conv.created_at = now
        conv.updated_at = now
        return await self.conversation_repo.create(conv)

    async def get_conversation(self, company_id: UUID, conversation_id: UUID) -> Conversation:
        """
        Retrieves a conversation metadata record.
        """
        conv = await self.conversation_repo.get_by_id(conversation_id)
        if not conv or conv.company_id != company_id:
            raise NotFoundException("Conversation session not found")
        return conv

    async def list_conversations(
        self,
        company_id: UUID,
        limit: int = 20,
        cursor: Optional[str] = None
    ) -> Tuple[List[Conversation], Optional[str], bool]:
        """
        Lists cursor-paginated conversations.
        """
        return await self.conversation_repo.list_conversations(company_id, limit, cursor)

    async def list_messages(
        self,
        company_id: UUID,
        conversation_id: UUID,
        limit: int = 50,
        cursor: Optional[str] = None
    ) -> Tuple[List[Message], Optional[str], bool]:
        """
        Lists cursor-paginated messages for a conversation.
        """
        # Validate conversation exists
        await self.get_conversation(company_id, conversation_id)
        return await self.message_repo.list_messages(conversation_id, limit, cursor)

    async def submit_feedback(
        self,
        company_id: UUID,
        conversation_id: UUID,
        message_id: UUID,
        score: int
    ) -> Message:
        """
        Submits feedback on a specific message.
        """
        # Validate conversation
        await self.get_conversation(company_id, conversation_id)

        msg = await self.message_repo.get_by_id(message_id)
        if not msg or msg.conversation_id != conversation_id:
            raise NotFoundException("Message not found")

        msg.feedback_score = score
        msg.updated_at = datetime.now(timezone.utc)
        updated = await self.message_repo.update(msg)
        if not updated:
            raise ConflictException("Failed to update message feedback score")
        return updated

    async def update_conversation_status(
        self,
        company_id: UUID,
        conversation_id: UUID,
        status: ConversationStatus
    ) -> Conversation:
        """
        Manually transitions conversation state (e.g. escalating to an agent).
        """
        conv = await self.get_conversation(company_id, conversation_id)
        conv.status = status
        conv.updated_at = datetime.now(timezone.utc)
        updated = await self.conversation_repo.update(conv)
        if not updated:
            raise ConflictException("Failed to update conversation status")
        return updated

    async def get_rag_context(self, company_id: UUID, content: str, threshold: float = 0.65) -> Tuple[List[str], List[Citation]]:
        """
        Executes vector search and returns text chunks and grounding citation objects.
        """
        # Generate query vector embedding
        query_vectors = await self.ai_service.generate_embeddings([content])
        if not query_vectors:
            return [], []
        
        query_vector = query_vectors[0]

        # Vector search company isolated chunks
        chunks = await self.document_repo.vector_search(
            company_id=company_id,
            query_vector=query_vector,
            min_score=threshold,
            limit=4
        )

        context_chunks = []
        citations = []
        for c in chunks:
            text = c.get("content", "")
            context_chunks.append(text)
            metadata = c.get("metadata", {})
            citations.append(Citation(
                document_id=c.get("document_id") or uuid.uuid4(),
                source_title=metadata.get("source_title", "Verified Knowledge Base"),
                chunk_index=c.get("chunk_index", 0)
            ))
        return context_chunks, citations

    async def process_user_message(
        self,
        company_id: UUID,
        conversation_id: UUID,
        content: str
    ) -> Tuple[Message, Message]:
        """
        Saves user query, runs RAG pipeline synchronously, checks grounding, and returns user + assistant messages.
        """
        conv = await self.get_conversation(company_id, conversation_id)

        now = datetime.now(timezone.utc)

        # 1. Save user query message
        user_msg = Message(
            message_id=uuid.uuid4(),
            conversation_id=conversation_id,
            company_id=company_id,
            sender_type=SenderType.USER,
            content=content,
            citations=[],
            feedback_score=0
        )
        user_msg.created_at = now
        user_msg.updated_at = now
        await self.message_repo.create(user_msg)

        # 2. Retrieve company setting configs
        system_prompt = "You are a helpful customer support assistant. Answer the user's questions based ONLY on the provided context facts. If the information is not in the context, respond with 'I do not have this information.'"
        confidence_threshold = 0.65
        temperature = 0.2
        max_tokens = 1024

        db: AsyncIOMotorDatabase = self.conversation_repo.db
        ai_set = await db["ai_settings"].find_one({"company_id": company_id, "is_deleted": False})
        if ai_set:
            system_prompt = ai_set.get("system_prompt", system_prompt)
            confidence_threshold = ai_set.get("confidence_threshold", confidence_threshold)
            temperature = ai_set.get("temperature", temperature)
            max_tokens = ai_set.get("max_tokens", max_tokens)

        # 3. Retrieve relevant grounding context chunks
        context_chunks, citations = await self.get_rag_context(company_id, content, confidence_threshold)

        # 4. Compile recent chat history context (last 6 messages)
        recent_history = await self.message_repo.get_recent_history(conversation_id, limit=6)
        formatted_history = []
        for h in recent_history:
            role = "model" if h.sender_type == SenderType.ASSISTANT else "user"
            formatted_history.append({"role": role, "content": h.content})

        # 5. Execute generative completion
        if not context_chunks:
            # Fallback if no context chunks match
            answer = "I am sorry, but I do not have enough verified information to answer your query. Let me escalate this to a support agent."
            conv.status = ConversationStatus.ESCALATED
        else:
            context_block = "\n\n".join(context_chunks)
            prompt = f"Context Facts:\n{context_block}\n\nUser Question:\n{content}"
            raw_answer = await self.ai_service.generate_completion(
                system_prompt=system_prompt,
                prompt=prompt,
                history=formatted_history,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Validate grounding of generated answer
            grounding_score = await self.ai_service.validate_grounding(context_chunks, raw_answer)
            if grounding_score < confidence_threshold:
                logger.warning(f"RAG Grounding safety score low ({grounding_score}). Falling back and escalating.")
                answer = "I am sorry, but I do not have enough verified information to answer your query. Let me escalate this to a support agent."
                conv.status = ConversationStatus.ESCALATED
                citations = []
            else:
                answer = raw_answer

        # 6. Save Assistant answer message
        now = datetime.now(timezone.utc)
        assistant_msg = Message(
            message_id=uuid.uuid4(),
            conversation_id=conversation_id,
            company_id=company_id,
            sender_type=SenderType.ASSISTANT,
            content=answer,
            citations=citations,
            feedback_score=0
        )
        assistant_msg.created_at = now
        assistant_msg.updated_at = now
        await self.message_repo.create(assistant_msg)

        # 7. Update Conversation last message timestamps
        conv.last_message_at = now
        conv.updated_at = now
        await self.conversation_repo.update(conv)

        return user_msg, assistant_msg


    # ==========================================
    # Product Catalog Methods
    # ==========================================

    async def create_product(self, company_id: UUID, payload: Product) -> Product:
        """
        Registers a product catalog item under the company tenant.
        """
        company = await self.company_repo.get_by_company_id(company_id)
        if not company:
            raise NotFoundException("Company workspace not found")

        # SKU uniqueness check
        existing = await self.product_repo.get_by_sku(company_id, payload.sku)
        if existing:
            raise DuplicateResourceException("Product with this SKU already exists in workspace")

        payload.company_id = company_id
        now = datetime.now(timezone.utc)
        payload.created_at = now
        payload.updated_at = now
        return await self.product_repo.create(payload)

    async def get_product(self, company_id: UUID, product_id: UUID) -> Product:
        """
        Retrieves a single product catalog item.
        """
        prod = await self.product_repo.get_by_id(product_id)
        if not prod or prod.company_id != company_id:
            raise NotFoundException("Product not found")
        return prod

    async def list_products(self, company_id: UUID) -> List[Product]:
        """
        Lists all products inside a tenant company workspace.
        """
        return await self.product_repo.list_products(company_id)

    async def search_products(self, company_id: UUID, query: str) -> List[Product]:
        """
        Searches catalog products matching text query.
        """
        return await self.product_repo.text_search(company_id, query)
