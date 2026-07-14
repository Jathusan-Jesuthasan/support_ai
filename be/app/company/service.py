import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID
from app.core.enums import CompanyStatus, MembershipRole, MembershipStatus
from app.shared.exceptions import (
    NotFoundException,
    DuplicateResourceException,
    AuthorizationException,
    ConflictException
)
from app.shared.utils import slugify
from app.company.model import Company, CompanyMember, CompanySettings
from app.company.schema import CompanyCreateRequest, CompanyUpdateRequest
from app.company.repository import CompanyRepository, CompanyMemberRepository


class CompanyService:
    """
    Coordinates tenant creation, RBAC authorization validations, unique slug suffix generation,
    and database operations to enforce company workspace business logic.
    """

    def __init__(
        self,
        company_repo: Optional[CompanyRepository] = None,
        member_repo: Optional[CompanyMemberRepository] = None
    ) -> None:
        self._company_repo = company_repo or CompanyRepository()
        self._member_repo = member_repo or CompanyMemberRepository()

    async def create_company(self, request: CompanyCreateRequest, creator_id: UUID) -> Company:
        """
        Creates a new tenant company workspace and automatically assigns the creator as OWNER.
        """
        # 1. Determine and validate unique slug
        if request.slug:
            slug = request.slug.strip().lower()
            if await self._company_repo.exists_by_slug(slug):
                raise DuplicateResourceException(f"Company slug '{slug}' is already taken")
        else:
            base_slug = slugify(request.name)
            if not base_slug:
                base_slug = "company"
            slug = base_slug
            counter = 2
            while await self._company_repo.exists_by_slug(slug):
                slug = f"{base_slug}-{counter}"
                counter += 1

        # 2. Instantiate Company document
        now = datetime.now(timezone.utc)
        company_id = uuid.uuid4()
        
        settings = CompanySettings()
        
        company = Company(
            company_id=company_id,
            name=request.name,
            slug=slug,
            status=CompanyStatus.ACTIVE,
            description=request.description,
            website=request.website,
            industry=request.industry,
            timezone=request.timezone,
            country=request.country,
            settings=settings,
            created_by=creator_id,
            updated_by=creator_id,
            created_at=now,
            updated_at=now
        )
        await self._company_repo.create(company)

        # 3. Automatically create active OWNER membership for the creator user
        membership_id = uuid.uuid4()
        member = CompanyMember(
            membership_id=membership_id,
            company_id=company_id,
            user_id=creator_id,
            role=MembershipRole.OWNER,
            status=MembershipStatus.ACTIVE,
            joined_at=now,
            last_active_at=now,
            created_by=creator_id,
            updated_by=creator_id,
            created_at=now,
            updated_at=now
        )
        await self._member_repo.create(member)

        return company

    async def get_company(self, company_id: UUID, user_id: UUID) -> Company:
        """
        Retrieves a company's details, verifying that the caller has a valid membership.
        """
        # Verify user belongs to the company
        membership = await self._member_repo.get_by_user_and_company(user_id, company_id)
        if not membership:
            raise AuthorizationException("You do not have permission to access this company")

        company = await self._company_repo.get_by_company_id(company_id)
        if not company:
            raise NotFoundException("Company workspace not found")

        return company

    async def update_company(self, company_id: UUID, request: CompanyUpdateRequest, user_id: UUID) -> Company:
        """
        Updates an existing company's properties.
        Only OWNER and ADMIN membership roles are allowed to perform updates.
        """
        # Verify user membership and RBAC role (OWNER or ADMIN)
        membership = await self._member_repo.get_by_user_and_company(user_id, company_id)
        if not membership:
            raise AuthorizationException("You do not have permission to access this company")

        if membership.role not in (MembershipRole.OWNER, MembershipRole.ADMIN):
            raise AuthorizationException("Only OWNER and ADMIN members may update company settings")

        company = await self._company_repo.get_by_company_id(company_id)
        if not company:
            raise NotFoundException("Company workspace not found")

        # Handle unique slug updates
        if request.slug and request.slug != company.slug:
            slug = request.slug.strip().lower()
            if await self._company_repo.exists_by_slug(slug):
                raise DuplicateResourceException(f"Company slug '{slug}' is already taken")
            company.slug = slug

        # Update other allowed fields
        if request.name is not None:
            company.name = request.name
        if request.description is not None:
            company.description = request.description
        if request.website is not None:
            company.website = request.website
        if request.industry is not None:
            company.industry = request.industry
        if request.timezone is not None:
            company.timezone = request.timezone
        if request.country is not None:
            company.country = request.country
        if request.status is not None:
            company.status = request.status

        # Save and check optimistic locking
        company.updated_by = user_id
        updated_company = await self._company_repo.update(company)
        if not updated_company:
            raise ConflictException("Company was modified by another request. Please try again.")

        return updated_company

    async def soft_delete_company(self, company_id: UUID, user_id: UUID) -> None:
        """
        Logically soft-deletes a company workspace and marks all active memberships as REMOVED.
        Only the OWNER of the company is allowed to delete it.
        """
        # Verify user membership and RBAC role (Only OWNER allowed)
        membership = await self._member_repo.get_by_user_and_company(user_id, company_id)
        if not membership:
            raise AuthorizationException("You do not have permission to access this company")

        if membership.role != MembershipRole.OWNER:
            raise AuthorizationException("Only the company OWNER may delete the workspace")

        company = await self._company_repo.get_by_company_id(company_id)
        if not company:
            raise NotFoundException("Company workspace not found")

        # Soft delete the company
        success = await self._company_repo.soft_delete(company_id, user_id)
        if not success:
            raise NotFoundException("Company workspace not found or already deleted")

        # Revoke/soft-delete memberships
        await self._member_repo.remove_all_company_members(company_id, user_id)

    async def list_user_companies(
        self,
        user_id: UUID,
        limit: int = 20,
        cursor: Optional[str] = None
    ) -> Tuple[List[Company], Optional[str], bool]:
        """
        Returns a paginated list of companies where the user has an active membership.
        """
        # 1. Fetch user memberships
        memberships, next_cursor, has_more = await self._member_repo.list_user_companies(
            user_id=user_id,
            limit=limit,
            cursor=cursor
        )

        # 2. Fetch corresponding company documents
        companies: List[Company] = []
        for m in memberships:
            company = await self._company_repo.get_by_company_id(m.company_id)
            if company:
                companies.append(company)

        return companies, next_cursor, has_more
