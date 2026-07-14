from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from app.core.dependencies import get_current_active_user
from app.auth.model import User
from app.company.schema import (
    CompanyCreateRequest,
    CompanyUpdateRequest,
    CompanyResponseEnvelope,
    CompanyListResponse,
    CompanyDeleteResponse,
    CompanyResponse,
    CompanyListItem,
    CursorPaginationMeta
)
from app.company.service import CompanyService

router = APIRouter()


def get_company_service() -> CompanyService:
    """
    FastAPI dependency yielding the active CompanyService instance.
    """
    return CompanyService()


@router.post(
    "",
    response_model=CompanyResponseEnvelope,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new company workspace"
)
async def create_company(
    request_payload: CompanyCreateRequest,
    current_user: User = Depends(get_current_active_user),
    service: CompanyService = Depends(get_company_service)
):
    """
    Registers a new company tenant workspace and automatically maps the creator user as the OWNER.
    """
    company = await service.create_company(request_payload, current_user.user_id)
    return CompanyResponseEnvelope(
        status="success",
        data=CompanyResponse(
            company_id=company.company_id,
            name=company.name,
            slug=company.slug,
            description=company.description,
            logo_url=company.logo_url,
            website=company.website,
            industry=company.industry,
            timezone=company.timezone,
            country=company.country,
            status=company.status,
            settings=company.settings,
            created_at=company.created_at,
            updated_at=company.updated_at
        )
    )


@router.get(
    "",
    response_model=CompanyListResponse,
    summary="List caller's company memberships"
)
async def list_companies(
    limit: int = Query(20, ge=1, le=100, description="Max number of records to return"),
    cursor: Optional[str] = Query(None, description="Base64 encoded cursor for pagination"),
    current_user: User = Depends(get_current_active_user),
    service: CompanyService = Depends(get_company_service)
):
    """
    Returns a cursor-paginated list of companies where the authenticated user is an active member.
    """
    companies, next_cursor, has_more = await service.list_user_companies(
        user_id=current_user.user_id,
        limit=limit,
        cursor=cursor
    )

    items = [
        CompanyListItem(
            company_id=c.company_id,
            name=c.name,
            slug=c.slug,
            status=c.status,
            created_at=c.created_at
        )
        for c in companies
    ]

    return CompanyListResponse(
        status="success",
        data=items,
        meta=CursorPaginationMeta(
            limit=limit,
            next_cursor=next_cursor,
            has_more=has_more
        )
    )


@router.get(
    "/{company_id}",
    response_model=CompanyResponseEnvelope,
    summary="Get company details by ID"
)
async def get_company(
    company_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: CompanyService = Depends(get_company_service)
):
    """
    Retrieves full details of a company workspace. Enforces caller membership checks.
    """
    company = await service.get_company(company_id, current_user.user_id)
    return CompanyResponseEnvelope(
        status="success",
        data=CompanyResponse(
            company_id=company.company_id,
            name=company.name,
            slug=company.slug,
            description=company.description,
            logo_url=company.logo_url,
            website=company.website,
            industry=company.industry,
            timezone=company.timezone,
            country=company.country,
            status=company.status,
            settings=company.settings,
            created_at=company.created_at,
            updated_at=company.updated_at
        )
    )


@router.put(
    "/{company_id}",
    response_model=CompanyResponseEnvelope,
    summary="Update company details"
)
async def update_company(
    company_id: UUID,
    request_payload: CompanyUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    service: CompanyService = Depends(get_company_service)
):
    """
    Updates configuration parameters of a company workspace. Enforces OWNER or ADMIN role checks.
    """
    company = await service.update_company(company_id, request_payload, current_user.user_id)
    return CompanyResponseEnvelope(
        status="success",
        data=CompanyResponse(
            company_id=company.company_id,
            name=company.name,
            slug=company.slug,
            description=company.description,
            logo_url=company.logo_url,
            website=company.website,
            industry=company.industry,
            timezone=company.timezone,
            country=company.country,
            status=company.status,
            settings=company.settings,
            created_at=company.created_at,
            updated_at=company.updated_at
        )
    )


@router.delete(
    "/{company_id}",
    response_model=CompanyDeleteResponse,
    summary="Soft delete a company workspace"
)
async def delete_company(
    company_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: CompanyService = Depends(get_company_service)
):
    """
    Logically soft-deletes a company workspace and revokes all active user memberships. Enforces OWNER role check.
    """
    await service.soft_delete_company(company_id, current_user.user_id)
    return CompanyDeleteResponse()
