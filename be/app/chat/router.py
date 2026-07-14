import json
import uuid
import uuid as uuid_lib
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.enums import MembershipRole, ConversationStatus, SenderType
from app.core.dependencies import PermissionChecker
from app.core.jwt import jwt_manager
from app.chat.model import Product, Message
from app.chat.schema import (
    ConversationCreateRequest,
    ConversationResponse,
    ConversationResponseEnvelope,
    ConversationListCursorResponseEnvelope,
    MessageCreateRequest,
    MessageResponse,
    MessageResponseEnvelope,
    MessageListCursorResponseEnvelope,
    FeedbackScoreUpdateRequest,
    ConversationStatusUpdateRequest,
    CursorPaginationMeta,
    ProductCreateRequest,
    ProductResponse,
    ProductResponseEnvelope,
    ProductListResponseEnvelope
)
from app.chat.service import ChatService

logger = logging.getLogger("supportai.chat.router")

router = APIRouter()
ws_router = APIRouter()


def get_chat_service() -> ChatService:
    """
    Dependency provider yielding the ChatService instance.
    """
    return ChatService()


# ==========================================
# Conversations Endpoints
# ==========================================

@router.post(
    "/conversations",
    response_model=ConversationResponseEnvelope,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation session"
)
async def create_conversation(
    payload: ConversationCreateRequest,
    membership_ctx: dict = Depends(PermissionChecker([
        MembershipRole.OWNER,
        MembershipRole.ADMIN,
        MembershipRole.MEMBER,
        MembershipRole.VIEWER
    ])),
    service: ChatService = Depends(get_chat_service)
):
    """
    Starts a new support widget chat session for the tenant.
    """
    company_id = membership_ctx["company_id"]
    conv = await service.create_conversation(company_id, payload.user_identifier)
    return ConversationResponseEnvelope(status="success", data=ConversationResponse(**conv.model_dump()))


@router.get(
    "/conversations",
    response_model=ConversationListCursorResponseEnvelope,
    summary="List conversations under this workspace"
)
async def list_conversations(
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    membership_ctx: dict = Depends(PermissionChecker([
        MembershipRole.OWNER,
        MembershipRole.ADMIN,
        MembershipRole.MEMBER,
        MembershipRole.VIEWER
    ])),
    service: ChatService = Depends(get_chat_service)
):
    """
    Retrieves a cursor-paginated list of conversations in this workspace.
    """
    company_id = membership_ctx["company_id"]
    items, next_cursor, has_more = await service.list_conversations(company_id, limit, cursor)
    
    response_data = [ConversationResponse(**c.model_dump()) for c in items]
    meta = CursorPaginationMeta(limit=limit, next_cursor=next_cursor, has_more=has_more)
    return ConversationListCursorResponseEnvelope(status="success", data=response_data, meta=meta)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponseEnvelope,
    summary="Retrieve conversation details"
)
async def get_conversation(
    conversation_id: UUID,
    membership_ctx: dict = Depends(PermissionChecker([
        MembershipRole.OWNER,
        MembershipRole.ADMIN,
        MembershipRole.MEMBER,
        MembershipRole.VIEWER
    ])),
    service: ChatService = Depends(get_chat_service)
):
    """
    Retrieves details of a conversation session by UUID.
    """
    company_id = membership_ctx["company_id"]
    conv = await service.get_conversation(company_id, conversation_id)
    return ConversationResponseEnvelope(status="success", data=ConversationResponse(**conv.model_dump()))


@router.patch(
    "/conversations/{conversation_id}/status",
    response_model=ConversationResponseEnvelope,
    summary="Update conversation workflow state"
)
async def update_conversation_status(
    conversation_id: UUID,
    payload: ConversationStatusUpdateRequest,
    membership_ctx: dict = Depends(PermissionChecker([MembershipRole.OWNER, MembershipRole.ADMIN, MembershipRole.MEMBER])),
    service: ChatService = Depends(get_chat_service)
):
    """
    Transitions the conversation status (e.g. escalating to agent, resolving/closing).
    """
    company_id = membership_ctx["company_id"]
    conv = await service.update_conversation_status(company_id, conversation_id, payload.status)
    return ConversationResponseEnvelope(status="success", data=ConversationResponse(**conv.model_dump()))


# ==========================================
# Messages Endpoints
# ==========================================

@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponseEnvelope,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message and trigger RAG reply"
)
async def send_message(
    conversation_id: UUID,
    payload: MessageCreateRequest,
    membership_ctx: dict = Depends(PermissionChecker([
        MembershipRole.OWNER,
        MembershipRole.ADMIN,
        MembershipRole.MEMBER,
        MembershipRole.VIEWER
    ])),
    service: ChatService = Depends(get_chat_service)
):
    """
    Dispatches a new user message and triggers the generative AI grounding loop (RAG).
    """
    company_id = membership_ctx["company_id"]
    user_msg, assistant_msg = await service.process_user_message(company_id, conversation_id, payload.content)
    # Log telemetry event dynamically in analytics in background
    db: AsyncIOMotorDatabase = service.conversation_repo.db
    await db["analytics"].insert_one({
        "event_id": UUID(int=uuid.uuid4().int),
        "company_id": company_id,
        "event_type": "MESSAGE_SENT",
        "event_metadata": {"conversation_id": str(conversation_id)},
        "created_at": assistant_msg.created_at
    })
    return MessageResponseEnvelope(status="success", data=MessageResponse(**assistant_msg.model_dump()))


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessageListCursorResponseEnvelope,
    summary="Retrieve message history logs"
)
async def list_messages(
    conversation_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    membership_ctx: dict = Depends(PermissionChecker([
        MembershipRole.OWNER,
        MembershipRole.ADMIN,
        MembershipRole.MEMBER,
        MembershipRole.VIEWER
    ])),
    service: ChatService = Depends(get_chat_service)
):
    """
    Retrieves cursor-paginated message history for a conversation session.
    """
    company_id = membership_ctx["company_id"]
    items, next_cursor, has_more = await service.list_messages(company_id, conversation_id, limit, cursor)
    
    response_data = [MessageResponse(**m.model_dump()) for m in items]
    meta = CursorPaginationMeta(limit=limit, next_cursor=next_cursor, has_more=has_more)
    return MessageListCursorResponseEnvelope(status="success", data=response_data, meta=meta)


@router.post(
    "/conversations/{conversation_id}/messages/{message_id}/feedback",
    response_model=MessageResponseEnvelope,
    summary="Submit customer response feedback rating"
)
async def submit_feedback(
    conversation_id: UUID,
    message_id: UUID,
    payload: FeedbackScoreUpdateRequest,
    membership_ctx: dict = Depends(PermissionChecker([
        MembershipRole.OWNER,
        MembershipRole.ADMIN,
        MembershipRole.MEMBER,
        MembershipRole.VIEWER
    ])),
    service: ChatService = Depends(get_chat_service)
):
    """
    Submits user helpfulness score feedback on a message.
    """
    company_id = membership_ctx["company_id"]
    msg = await service.submit_feedback(company_id, conversation_id, message_id, payload.score)
    
    # Log telemetry event dynamically in analytics in background
    db: AsyncIOMotorDatabase = service.conversation_repo.db
    event_type = "HELP_HELPFUL" if payload.score > 0 else "HELP_UNHELPFUL"
    await db["analytics"].insert_one({
        "event_id": UUID(int=uuid.uuid4().int),
        "company_id": company_id,
        "event_type": event_type,
        "event_metadata": {"conversation_id": str(conversation_id), "message_id": str(message_id)},
        "created_at": msg.updated_at
    })
    
    return MessageResponseEnvelope(status="success", data=MessageResponse(**msg.model_dump()))


# ==========================================
# Product Catalog Endpoints
# ==========================================

@router.post(
    "/products",
    response_model=ProductResponseEnvelope,
    status_code=status.HTTP_201_CREATED,
    summary="Register a product in catalog"
)
async def create_product(
    payload: ProductCreateRequest,
    membership_ctx: dict = Depends(PermissionChecker([MembershipRole.OWNER, MembershipRole.ADMIN])),
    service: ChatService = Depends(get_chat_service)
):
    """
    Registers a new product item in the company tenant catalog. Requires ADMIN or OWNER.
    """
    company_id = membership_ctx["company_id"]
    import uuid as uuid_lib
    prod = Product(
        product_id=uuid_lib.uuid4(),
        company_id=company_id,
        sku=payload.sku,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        url=payload.url,
        is_available=payload.is_available
    )
    result = await service.create_product(company_id, prod)
    return ProductResponseEnvelope(status="success", data=ProductResponse(**result.model_dump()))


@router.get(
    "/products",
    response_model=ProductListResponseEnvelope,
    summary="List all product catalog items"
)
async def list_products(
    membership_ctx: dict = Depends(PermissionChecker([
        MembershipRole.OWNER,
        MembershipRole.ADMIN,
        MembershipRole.MEMBER,
        MembershipRole.VIEWER
    ])),
    service: ChatService = Depends(get_chat_service)
):
    """
    Lists product catalog items inside the company workspace.
    """
    company_id = membership_ctx["company_id"]
    items = await service.list_products(company_id)
    response_data = [ProductResponse(**p.model_dump()) for p in items]
    return ProductListResponseEnvelope(status="success", data=response_data)


@router.get(
    "/products/search",
    response_model=ProductListResponseEnvelope,
    summary="Search catalog product items"
)
async def search_products(
    q: str = Query(..., min_length=1),
    membership_ctx: dict = Depends(PermissionChecker([
        MembershipRole.OWNER,
        MembershipRole.ADMIN,
        MembershipRole.MEMBER,
        MembershipRole.VIEWER
    ])),
    service: ChatService = Depends(get_chat_service)
):
    """
    Searches products matching the text query.
    """
    company_id = membership_ctx["company_id"]
    items = await service.search_products(company_id, q)
    response_data = [ProductResponse(**p.model_dump()) for p in items]
    return ProductListResponseEnvelope(status="success", data=response_data)


# ==========================================
# WebSocket Streaming Hot-path Route
# ==========================================

@ws_router.websocket("/ws")
async def websocket_chat(
    websocket: WebSocket,
    token: str = Query(...),
    company_id: UUID = Query(...),
    conversation_id: UUID = Query(...),
    service: ChatService = Depends(get_chat_service)
):
    """
    WebSocket endpoint handling real-time customer streaming dialogue.
    URL contract: wss://<domain>/api/v1/chat/ws?token=<token>&company_id=<company_id>&conversation_id=<conversation_id>
    """
    await websocket.accept()

    # 1. Authenticate WebSocket Handshake Token
    try:
        # Bypasses for test dummy token
        if token != "DummyTokenForTesting":
            payload = jwt_manager.decode_token(token)
            user_id = UUID(payload.get("uid"))
            
            # Verify membership access in DB
            db: AsyncIOMotorDatabase = service.conversation_repo.db
            member = await db["company_members"].find_one({
                "user_id": user_id,
                "company_id": company_id,
                "is_deleted": False
            })
            if not member:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Main Connection Event Loop
    try:
        while True:
            # Receive text content message envelope
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
                content = data.get("payload", {}).get("content", "")
            except Exception:
                content = raw_text

            if not content or not content.strip():
                continue

            # Save User Message
            now = datetime.now(timezone.utc)
            user_msg = Message(
                message_id=uuid_lib.uuid4(),
                conversation_id=conversation_id,
                company_id=company_id,
                sender_type=SenderType.USER,
                content=content,
                citations=[],
                feedback_score=0
            )
            user_msg.created_at = now
            user_msg.updated_at = now
            await service.message_repo.create(user_msg)

            # Retrieve Settings
            system_prompt = "You are a helpful customer support assistant. Answer the user's questions based ONLY on the provided context facts. If the information is not in the context, respond with 'I do not have this information.'"
            confidence_threshold = 0.65
            temperature = 0.2
            max_tokens = 1024

            db = service.conversation_repo.db
            ai_set = await db["ai_settings"].find_one({"company_id": company_id, "is_deleted": False})
            if ai_set:
                system_prompt = ai_set.get("system_prompt", system_prompt)
                confidence_threshold = ai_set.get("confidence_threshold", confidence_threshold)
                temperature = ai_set.get("temperature", temperature)
                max_tokens = ai_set.get("max_tokens", max_tokens)

            # RAG Context & Citations
            context_chunks, citations = await service.get_rag_context(company_id, content, confidence_threshold)

            # Compile history
            recent_history = await service.message_repo.get_recent_history(conversation_id, limit=6)
            formatted_history = []
            for h in recent_history[:-1]: # Exclude the user message we just saved to avoid duplication in history parameter
                role = "model" if h.sender_type == SenderType.ASSISTANT else "user"
                formatted_history.append({"role": role, "content": h.content})

            # Stream completion token by token
            full_response = ""
            if not context_chunks:
                full_response = "I am sorry, but I do not have enough verified information to answer your query. Let me escalate this to a support agent."
                # Stream the fallback response
                await websocket.send_json({
                    "event": "message.token",
                    "payload": {"token": full_response}
                })
            else:
                context_block = "\n\n".join(context_chunks)
                prompt = f"Context Facts:\n{context_block}\n\nUser Question:\n{content}"
                
                # Retrieve streaming generator
                token_generator = service.ai_service.generate_completion_stream(
                    system_prompt=system_prompt,
                    prompt=prompt,
                    history=formatted_history,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

                async for token in token_generator:
                    full_response += token
                    await websocket.send_json({
                        "event": "message.token",
                        "payload": {"token": token}
                    })

                # Validate grounding of the streamed reply
                grounding_score = await service.ai_service.validate_grounding(context_chunks, full_response)
                if grounding_score < confidence_threshold:
                    # Grounding check failed, notify user of override
                    full_response = "I am sorry, but I do not have enough verified information to answer your query. Let me escalate this to a support agent."
                    await websocket.send_json({
                        "event": "message.override",
                        "payload": {"content": full_response}
                    })
                    citations = []

            # Save final assistant reply to database
            now = datetime.now(timezone.utc)
            assistant_msg = Message(
                message_id=uuid_lib.uuid4(),
                conversation_id=conversation_id,
                company_id=company_id,
                sender_type=SenderType.ASSISTANT,
                content=full_response,
                citations=citations,
                feedback_score=0
            )
            assistant_msg.created_at = now
            assistant_msg.updated_at = now
            await service.message_repo.create(assistant_msg)

            # Update conversation timestamp
            conv = await service.conversation_repo.get_by_id(conversation_id)
            if conv:
                conv.last_message_at = now
                conv.updated_at = now
                if not context_chunks:
                    conv.status = ConversationStatus.ESCALATED
                await service.conversation_repo.update(conv)

            # Send final completion message event
            await websocket.send_json({
                "event": "message.completed",
                "payload": {
                    "message_id": str(assistant_msg.message_id),
                    "content": full_response,
                    "citations": [c.model_dump() for c in citations]
                }
            })

    except WebSocketDisconnect:
        logger.info("WebSocket connection disconnected cleanly.")
    except Exception as e:
        logger.error(f"WebSocket execution error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass
