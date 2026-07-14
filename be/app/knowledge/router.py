from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, status

from app.core.enums import MembershipRole
from app.core.dependencies import get_current_active_user, PermissionChecker
from app.auth.model import User
from app.knowledge.schema import (
    KnowledgeCreateRequest,
    KnowledgeResponse,
    KnowledgeResponseEnvelope,
    KnowledgeListResponseEnvelope
)
from app.knowledge.service import KnowledgeService

router = APIRouter()


def get_knowledge_service() -> KnowledgeService:
    """
    Dependency provider yielding the KnowledgeService instance.
    """
    return KnowledgeService()


@router.post(
    "",
    response_model=KnowledgeResponseEnvelope,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new knowledge base source reference"
)
async def create_knowledge(
    payload: KnowledgeCreateRequest,
    current_user: User = Depends(get_current_active_user),
    membership_ctx: dict = Depends(PermissionChecker([MembershipRole.OWNER, MembershipRole.ADMIN])),
    service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    Registers a new knowledge source. Requires OWNER or ADMIN role.
    """
    company_id = membership_ctx["company_id"]
    k = await service.create_knowledge(
        company_id=company_id,
        name=payload.name,
        description=payload.description,
        source_type=payload.source_type,
        creator_id=current_user.user_id
    )
    return KnowledgeResponseEnvelope(status="success", data=KnowledgeResponse(**k.model_dump()))


@router.post(
    "/{knowledge_id}/upload",
    response_model=KnowledgeResponseEnvelope,
    summary="Upload a file for parsing and vector indexing"
)
async def upload_document(
    knowledge_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    membership_ctx: dict = Depends(PermissionChecker([MembershipRole.OWNER, MembershipRole.ADMIN])),
    service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    Uploads a document (PDF, TXT, MD, DOCX) and kicks off background parsing. Requires OWNER or ADMIN role.
    """
    company_id = membership_ctx["company_id"]
    k = await service.upload_document_file(
        company_id=company_id,
        knowledge_id=knowledge_id,
        file=file,
        creator_id=current_user.user_id
    )
    return KnowledgeResponseEnvelope(status="success", data=KnowledgeResponse(**k.model_dump()))


@router.get(
    "/{knowledge_id}",
    response_model=KnowledgeResponseEnvelope,
    summary="Retrieve knowledge source status and details"
)
async def get_knowledge(
    knowledge_id: UUID,
    membership_ctx: dict = Depends(PermissionChecker([
        MembershipRole.OWNER,
        MembershipRole.ADMIN,
        MembershipRole.MEMBER,
        MembershipRole.VIEWER
    ])),
    service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    Retrieves details of a knowledge source. Requires active workspace membership.
    """
    company_id = membership_ctx["company_id"]
    k = await service.get_knowledge(company_id=company_id, knowledge_id=knowledge_id)
    return KnowledgeResponseEnvelope(status="success", data=KnowledgeResponse(**k.model_dump()))


@router.get(
    "",
    response_model=KnowledgeListResponseEnvelope,
    summary="List all workspace knowledge sources"
)
async def list_knowledge(
    membership_ctx: dict = Depends(PermissionChecker([
        MembershipRole.OWNER,
        MembershipRole.ADMIN,
        MembershipRole.MEMBER,
        MembershipRole.VIEWER
    ])),
    service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    Lists all knowledge sources in the company workspace.
    """
    company_id = membership_ctx["company_id"]
    sources = await service.list_knowledge(company_id)
    response_data = [KnowledgeResponse(**s.model_dump()) for s in sources]
    return KnowledgeListResponseEnvelope(status="success", data=response_data)


@router.delete(
    "/{knowledge_id}",
    status_code=status.HTTP_200_OK,
    summary="Archive/Delete a knowledge source"
)
async def delete_knowledge(
    knowledge_id: UUID,
    current_user: User = Depends(get_current_active_user),
    membership_ctx: dict = Depends(PermissionChecker([MembershipRole.OWNER, MembershipRole.ADMIN])),
    service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    Deletes a knowledge source and all its vectorized index data. Requires OWNER or ADMIN role.
    """
    company_id = membership_ctx["company_id"]
    await service.delete_knowledge(
        company_id=company_id,
        knowledge_id=knowledge_id,
        modifier_id=current_user.user_id
    )
    return {"status": "success", "message": "Knowledge source successfully deleted"}
