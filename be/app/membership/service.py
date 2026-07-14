import uuid
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from app.core.enums import MembershipRole, MembershipStatus
from app.shared.exceptions import (
    NotFoundException,
    DuplicateResourceException,
    AuthorizationException,
    ConflictException
)
from app.company.model import CompanyMember
from app.auth.repository import UserRepository
from app.company.repository import CompanyRepository
from app.membership.repository import MembershipRepository


class MembershipService:
    """
    Coordinates workspace memberships, roles, invitations, and permissions.
    """

    def __init__(
        self,
        membership_repo: Optional[MembershipRepository] = None,
        user_repo: Optional[UserRepository] = None,
        company_repo: Optional[CompanyRepository] = None
    ) -> None:
        self.membership_repo = membership_repo or MembershipRepository()
        self.user_repo = user_repo or UserRepository()
        self.company_repo = company_repo or CompanyRepository()

    async def invite_member(
        self,
        company_id: UUID,
        email: str,
        role: MembershipRole,
        creator_id: UUID
    ) -> CompanyMember:
        """
        Invites a user by email to join a company workspace.
        """
        # 1. Verify company workspace exists
        company = await self.company_repo.get_by_company_id(company_id)
        if not company:
            raise NotFoundException("Company workspace not found")

        # 2. Retrieve user by email
        user = await self.user_repo.get_by_email(email)
        if not user or user.is_deleted:
            raise NotFoundException(f"User with email '{email}' does not exist")

        # 3. Check for existing membership (even if soft-deleted or invited)
        existing = await self.membership_repo.get_by_user_and_company(user.user_id, company_id, include_deleted=True)
        if existing:
            if not existing.is_deleted and existing.status in (MembershipStatus.ACTIVE, MembershipStatus.INVITED):
                raise DuplicateResourceException("User is already a member or has a pending invitation")
            # If soft-deleted or removed, we can restore it
            existing.is_deleted = False
            existing.deleted_at = None
            existing.status = MembershipStatus.INVITED
            existing.role = role
            existing.invited_by = creator_id
            existing.update_audit(creator_id)
            updated = await self.membership_repo.update(existing)
            if not updated:
                raise ConflictException("Membership update conflict. Please try again.")
            return updated

        # 4. Create new membership
        now = datetime.now(timezone.utc)
        member = CompanyMember(
            membership_id=uuid.uuid4(),
            company_id=company_id,
            user_id=user.user_id,
            role=role,
            status=MembershipStatus.INVITED,
            invited_by=creator_id,
            created_by=creator_id,
            updated_by=creator_id,
            created_at=now,
            updated_at=now
        )
        return await self.membership_repo.create(member)

    async def accept_invitation(self, company_id: UUID, user_id: UUID) -> CompanyMember:
        """
        Accepts a pending invitation, transitioning the status to ACTIVE.
        """
        membership = await self.membership_repo.get_by_user_and_company(user_id, company_id)
        if not membership:
            raise NotFoundException("Pending invitation not found")

        if membership.status != MembershipStatus.INVITED:
            raise ConflictException("Invitation has already been accepted or is inactive")

        now = datetime.now(timezone.utc)
        membership.status = MembershipStatus.ACTIVE
        membership.joined_at = now
        membership.last_active_at = now
        membership.update_audit(user_id)
        
        updated = await self.membership_repo.update(membership)
        if not updated:
            raise ConflictException("Failed to accept invitation due to a state conflict")
        return updated

    async def update_membership(
        self,
        company_id: UUID,
        membership_id: UUID,
        role: Optional[MembershipRole],
        status: Optional[MembershipStatus],
        modifier_id: UUID
    ) -> CompanyMember:
        """
        Updates the role or status of an existing workspace membership.
        Enforces that only OWNER or ADMIN roles can modify membership, and ADMINs cannot demote/modify OWNERs.
        """
        # 1. Retrieve target membership
        target = await self.membership_repo.get_by_membership_id(membership_id)
        if not target or target.company_id != company_id:
            raise NotFoundException("Membership record not found in this company")

        # 2. Retrieve modifier's membership
        modifier = await self.membership_repo.get_by_user_and_company(modifier_id, company_id)
        if not modifier:
            raise AuthorizationException("Modifier is not a member of the workspace")

        # 3. Fine-grained RBAC checks
        # Only OWNER can demote/change an OWNER or set role to OWNER
        if target.role == MembershipRole.OWNER and modifier.role != MembershipRole.OWNER:
            raise AuthorizationException("Only the OWNER can modify OWNER membership")
        if role == MembershipRole.OWNER and modifier.role != MembershipRole.OWNER:
            raise AuthorizationException("Only the OWNER can designate a new OWNER")

        # If demoting an OWNER to a non-OWNER role, verify it is not the last OWNER
        if target.role == MembershipRole.OWNER and role is not None and role != MembershipRole.OWNER:
            db = self.membership_repo.db
            active_owners_count = await db["company_members"].count_documents({
                "company_id": company_id,
                "role": MembershipRole.OWNER.value,
                "status": MembershipStatus.ACTIVE.value,
                "is_deleted": False
            })
            if active_owners_count <= 1:
                raise ConflictException("Cannot demote the last OWNER of a company")

        # ADMIN cannot edit target ADMIN or higher
        if modifier.role == MembershipRole.ADMIN and target.role in (MembershipRole.OWNER, MembershipRole.ADMIN) and target.user_id != modifier_id:
            raise AuthorizationException("ADMIN members cannot modify other ADMIN or OWNER memberships")

        # 4. Perform updates
        if role is not None:
            target.role = role
        if status is not None:
            target.status = status
            if status == MembershipStatus.ACTIVE and not target.joined_at:
                target.joined_at = datetime.now(timezone.utc)

        target.update_audit(modifier_id)
        updated = await self.membership_repo.update(target)
        if not updated:
            raise ConflictException("Membership update conflict. Please try again.")
        return updated

    async def get_member(self, company_id: UUID, membership_id: UUID) -> CompanyMember:
        """
        Retrieves a single membership record.
        """
        member = await self.membership_repo.get_by_membership_id(membership_id)
        if not member or member.company_id != company_id:
            raise NotFoundException("Membership record not found")
        return member

    async def reject_invitation(self, company_id: UUID, user_id: UUID) -> CompanyMember:
        """
        Rejects a pending invitation, transitioning the status to REMOVED.
        """
        membership = await self.membership_repo.get_by_user_and_company(user_id, company_id)
        if not membership:
            raise NotFoundException("Pending invitation not found")

        if membership.status != MembershipStatus.INVITED:
            raise ConflictException("Invitation is not in a pending state")

        now = datetime.now(timezone.utc)
        membership.status = MembershipStatus.REMOVED
        membership.is_deleted = True
        membership.deleted_at = now
        membership.update_audit(user_id)

        updated = await self.membership_repo.update(membership)
        if not updated:
            raise ConflictException("Failed to reject invitation due to a state conflict")
        return updated

    async def leave_company(self, company_id: UUID, user_id: UUID) -> bool:
        """
        Removes current user's membership from the workspace.
        Enforces that the last active owner cannot leave.
        """
        membership = await self.membership_repo.get_by_user_and_company(user_id, company_id)
        if not membership:
            raise NotFoundException("Membership not found")

        if membership.role == MembershipRole.OWNER:
            db = self.membership_repo.db
            active_owners_count = await db["company_members"].count_documents({
                "company_id": company_id,
                "role": MembershipRole.OWNER.value,
                "status": MembershipStatus.ACTIVE.value,
                "is_deleted": False
            })
            if active_owners_count <= 1:
                raise ConflictException("Cannot leave company as the last OWNER. Transfer ownership first.")

        return await self.membership_repo.soft_delete(membership.membership_id, user_id)

    async def transfer_ownership(self, company_id: UUID, current_owner_id: UUID, target_user_id: UUID) -> CompanyMember:
        """
        Transfers the OWNER role to another active member, and demotes current owner to ADMIN.
        """
        owner_member = await self.membership_repo.get_by_user_and_company(current_owner_id, company_id)
        if not owner_member or owner_member.role != MembershipRole.OWNER:
            raise AuthorizationException("Only the company OWNER can transfer ownership")

        target_member = await self.membership_repo.get_by_user_and_company(target_user_id, company_id)
        if not target_member or target_member.status != MembershipStatus.ACTIVE:
            raise NotFoundException("Target user is not an active member of this company")

        # Atomic transaction-like updates
        target_member.role = MembershipRole.OWNER
        target_member.update_audit(current_owner_id)
        await self.membership_repo.update(target_member)

        owner_member.role = MembershipRole.ADMIN
        owner_member.update_audit(current_owner_id)
        await self.membership_repo.update(owner_member)

        return target_member

    async def remove_member(self, company_id: UUID, membership_id: UUID, modifier_id: UUID) -> bool:
        """
        Soft-deletes/removes a membership from the company workspace.
        Enforces that the last active owner cannot be removed.
        """
        target = await self.membership_repo.get_by_membership_id(membership_id)
        if not target or target.company_id != company_id:
            raise NotFoundException("Membership record not found")

        modifier = await self.membership_repo.get_by_user_and_company(modifier_id, company_id)
        if not modifier:
            raise AuthorizationException("Modifier is not a member of this workspace")

        # Enforce OWNER/ADMIN rules
        if target.role == MembershipRole.OWNER:
            if modifier.role != MembershipRole.OWNER:
                raise AuthorizationException("Only the OWNER can remove the OWNER membership")
            db = self.membership_repo.db
            active_owners_count = await db["company_members"].count_documents({
                "company_id": company_id,
                "role": MembershipRole.OWNER.value,
                "status": MembershipStatus.ACTIVE.value,
                "is_deleted": False
            })
            if active_owners_count <= 1:
                raise ConflictException("Cannot remove the last OWNER of a company")

        if modifier.role == MembershipRole.ADMIN and target.role in (MembershipRole.OWNER, MembershipRole.ADMIN) and target.user_id != modifier_id:
            raise AuthorizationException("ADMIN members cannot remove other ADMIN or OWNER memberships")

        return await self.membership_repo.soft_delete(membership_id, modifier_id)

    async def list_members(self, company_id: UUID) -> List[CompanyMember]:
        """
        Lists all active memberships inside a company.
        """
        memberships, _, _ = await self.membership_repo.list_company_members(company_id, limit=1000)
        return memberships
