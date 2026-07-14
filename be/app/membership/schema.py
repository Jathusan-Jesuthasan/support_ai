from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr
from app.core.enums import MembershipRole, MembershipStatus


class MembershipInviteRequest(BaseModel):
    email: EmailStr = Field(..., description="The email address of the user to invite")
    role: MembershipRole = Field(MembershipRole.MEMBER, description="The RBAC role to grant the user")


class MembershipUpdateRequest(BaseModel):
    role: Optional[MembershipRole] = Field(None, description="The updated RBAC role of the member")
    status: Optional[MembershipStatus] = Field(None, description="The updated status of the membership")


class MembershipRoleUpdateRequest(BaseModel):
    role: MembershipRole = Field(..., description="The updated RBAC role of the member")


class MembershipTransferOwnerRequest(BaseModel):
    target_user_id: UUID = Field(..., description="The user UUID to transfer ownership to")


class MembershipResponse(BaseModel):
    membership_id: UUID = Field(..., description="Unique membership UUID identifier")
    company_id: UUID = Field(..., description="The company workspace UUID reference")
    user_id: UUID = Field(..., description="The user UUID reference")
    role: MembershipRole = Field(..., description="The RBAC role of the user")
    status: MembershipStatus = Field(..., description="The status of the membership")
    invited_by: Optional[UUID] = Field(None, description="UUID of the user who issued the invitation")
    joined_at: Optional[datetime] = Field(None, description="UTC timestamp when user accepted invitation")
    last_active_at: Optional[datetime] = Field(None, description="UTC timestamp of the member's last activity")
    created_at: datetime = Field(..., description="UTC creation timestamp")
    updated_at: datetime = Field(..., description="UTC last update timestamp")


class MembershipResponseEnvelope(BaseModel):
    status: str = "success"
    data: MembershipResponse


class MembershipListResponseEnvelope(BaseModel):
    status: str = "success"
    data: List[MembershipResponse]
