from uuid import UUID
from fastapi import APIRouter, Depends, Header, status

from app.core.enums import MembershipRole
from app.core.dependencies import get_current_active_user, PermissionChecker
from app.auth.model import User
from app.membership.schema import (
    MembershipInviteRequest,
    MembershipRoleUpdateRequest,
    MembershipTransferOwnerRequest,
    MembershipResponse,
    MembershipResponseEnvelope,
    MembershipListResponseEnvelope
)
from app.membership.service import MembershipService

router = APIRouter()


def get_membership_service() -> MembershipService:
    """
    Dependency provider yielding the MembershipService instance.
    """
    return MembershipService()


@router.post(
    "/invite",
    response_model=MembershipResponseEnvelope,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a user to the company workspace"
)
async def invite_member(
    payload: MembershipInviteRequest,
    current_user: User = Depends(get_current_active_user),
    membership_ctx: dict = Depends(PermissionChecker([MembershipRole.OWNER, MembershipRole.ADMIN])),
    service: MembershipService = Depends(get_membership_service)
):
    """
    Invites a user by email to join the company workspace. Requires OWNER or ADMIN role.
    """
    company_id = membership_ctx["company_id"]
    member = await service.invite_member(
        company_id=company_id,
        email=str(payload.email),
        role=payload.role,
        creator_id=current_user.user_id
    )
    return MembershipResponseEnvelope(status="success", data=MembershipResponse(**member.model_dump()))


@router.post(
    "/accept",
    response_model=MembershipResponseEnvelope,
    summary="Accept a pending workspace invitation"
)
async def accept_invitation(
    company_id: UUID = Header(..., alias="X-Company-ID", description="The company workspace ID to join"),
    current_user: User = Depends(get_current_active_user),
    service: MembershipService = Depends(get_membership_service)
):
    """
    Accepts a pending invitation to join a workspace.
    """
    member = await service.accept_invitation(company_id=company_id, user_id=current_user.user_id)
    return MembershipResponseEnvelope(status="success", data=MembershipResponse(**member.model_dump()))


@router.post(
    "/reject",
    response_model=MembershipResponseEnvelope,
    summary="Reject a pending workspace invitation"
)
async def reject_invitation(
    company_id: UUID = Header(..., alias="X-Company-ID", description="The company workspace ID to reject"),
    current_user: User = Depends(get_current_active_user),
    service: MembershipService = Depends(get_membership_service)
):
    """
    Rejects a pending invitation to join a workspace.
    """
    member = await service.reject_invitation(company_id=company_id, user_id=current_user.user_id)
    return MembershipResponseEnvelope(status="success", data=MembershipResponse(**member.model_dump()))


@router.get(
    "",
    response_model=MembershipListResponseEnvelope,
    summary="List all company workspace members"
)
async def list_members(
    membership_ctx: dict = Depends(PermissionChecker([
        MembershipRole.OWNER,
        MembershipRole.ADMIN,
        MembershipRole.MEMBER,
        MembershipRole.VIEWER
    ])),
    service: MembershipService = Depends(get_membership_service)
):
    """
    Lists all members of the company workspace. Requires active membership.
    """
    company_id = membership_ctx["company_id"]
    members = await service.list_members(company_id)
    response_data = [MembershipResponse(**m.model_dump()) for m in members]
    return MembershipListResponseEnvelope(status="success", data=response_data)


@router.get(
    "/{id}",
    response_model=MembershipResponseEnvelope,
    summary="Retrieve a specific workspace membership record"
)
async def get_member(
    id: UUID,
    membership_ctx: dict = Depends(PermissionChecker([
        MembershipRole.OWNER,
        MembershipRole.ADMIN,
        MembershipRole.MEMBER,
        MembershipRole.VIEWER
    ])),
    service: MembershipService = Depends(get_membership_service)
):
    """
    Retrieves details of a membership. Requires active workspace membership.
    """
    company_id = membership_ctx["company_id"]
    member = await service.get_member(company_id=company_id, membership_id=id)
    return MembershipResponseEnvelope(status="success", data=MembershipResponse(**member.model_dump()))


@router.patch(
    "/{id}/role",
    response_model=MembershipResponseEnvelope,
    summary="Update a workspace membership role"
)
async def update_member_role(
    id: UUID,
    payload: MembershipRoleUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    membership_ctx: dict = Depends(PermissionChecker([MembershipRole.OWNER, MembershipRole.ADMIN])),
    service: MembershipService = Depends(get_membership_service)
):
    """
    Updates the role of a member. Requires OWNER or ADMIN role.
    """
    company_id = membership_ctx["company_id"]
    member = await service.update_membership(
        company_id=company_id,
        membership_id=id,
        role=payload.role,
        status=None,
        modifier_id=current_user.user_id
    )
    return MembershipResponseEnvelope(status="success", data=MembershipResponse(**member.model_dump()))


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Remove a member from the company workspace"
)
async def remove_member(
    id: UUID,
    current_user: User = Depends(get_current_active_user),
    membership_ctx: dict = Depends(PermissionChecker([MembershipRole.OWNER, MembershipRole.ADMIN])),
    service: MembershipService = Depends(get_membership_service)
):
    """
    Removes a member from the company workspace. Requires OWNER or ADMIN role.
    """
    company_id = membership_ctx["company_id"]
    await service.remove_member(
        company_id=company_id,
        membership_id=id,
        modifier_id=current_user.user_id
    )
    return {"status": "success", "message": "Membership successfully removed"}


@router.post(
    "/leave",
    status_code=status.HTTP_200_OK,
    summary="Leave the company workspace"
)
async def leave_company(
    company_id: UUID = Header(..., alias="X-Company-ID", description="The company workspace ID to leave"),
    current_user: User = Depends(get_current_active_user),
    service: MembershipService = Depends(get_membership_service)
):
    """
    Leaves the company workspace. Enforces that the last active OWNER cannot leave.
    """
    await service.leave_company(company_id=company_id, user_id=current_user.user_id)
    return {"status": "success", "message": "Successfully left the company workspace"}


@router.post(
    "/transfer-owner",
    response_model=MembershipResponseEnvelope,
    summary="Transfer ownership of the company workspace"
)
async def transfer_ownership(
    payload: MembershipTransferOwnerRequest,
    current_user: User = Depends(get_current_active_user),
    membership_ctx: dict = Depends(PermissionChecker([MembershipRole.OWNER])),
    service: MembershipService = Depends(get_membership_service)
):
    """
    Transfers OWNER role to another active member. Requires caller to be current OWNER.
    """
    company_id = membership_ctx["company_id"]
    member = await service.transfer_ownership(
        company_id=company_id,
        current_owner_id=current_user.user_id,
        target_user_id=payload.target_user_id
    )
    return MembershipResponseEnvelope(status="success", data=MembershipResponse(**member.model_dump()))
