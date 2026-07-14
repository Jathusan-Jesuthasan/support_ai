import hashlib
import json
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Header, Request, Response, status

from app.core.enums import MembershipRole
from app.core.dependencies import get_current_active_user, PermissionChecker
from app.auth.model import User
from app.shared.exceptions import AuthorizationException
from app.widget.schema import (
    WidgetSettingsUpdateRequest,
    WidgetSettingsResponse,
    WidgetSettingsResponseEnvelope,
    WidgetSettingsPublicConfigResponse,
    WidgetSettingsPublicConfigResponseEnvelope
)
from app.widget.service import WidgetService

# Admin endpoints router
admin_router = APIRouter()
# Public endpoints router
public_router = APIRouter()


def get_widget_service() -> WidgetService:
    """
    Dependency provider yielding the WidgetService instance.
    """
    return WidgetService()


# ==========================================
# Admin Endpoints (Tenant Restricted)
# ==========================================

@admin_router.get(
    "/widget/settings",
    response_model=WidgetSettingsResponseEnvelope,
    summary="Retrieve company widget UI and CORS configurations"
)
async def get_widget_settings(
    current_user: User = Depends(get_current_active_user),
    membership_ctx: dict = Depends(PermissionChecker([MembershipRole.OWNER, MembershipRole.ADMIN])),
    service: WidgetService = Depends(get_widget_service)
):
    """
    Retrieves the widget settings for the workspace. Requires OWNER or ADMIN.
    """
    company_id = membership_ctx["company_id"]
    settings = await service.get_or_create_settings(company_id, current_user.user_id)
    return WidgetSettingsResponseEnvelope(status="success", data=WidgetSettingsResponse(**settings.model_dump()))


@admin_router.put(
    "/widget/settings",
    response_model=WidgetSettingsResponseEnvelope,
    summary="Update company widget UI and CORS configurations"
)
async def update_widget_settings(
    payload: WidgetSettingsUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    membership_ctx: dict = Depends(PermissionChecker([MembershipRole.OWNER, MembershipRole.ADMIN])),
    service: WidgetService = Depends(get_widget_service)
):
    """
    Updates theme customisations or domain whitelists. Requires OWNER or ADMIN.
    """
    company_id = membership_ctx["company_id"]
    settings = await service.update_settings(company_id, payload, current_user.user_id)
    return WidgetSettingsResponseEnvelope(status="success", data=WidgetSettingsResponse(**settings.model_dump()))


# ==========================================
# Public Endpoints (Anonymous Access)
# ==========================================

@public_router.get(
    "/{company_id}/config",
    response_model=WidgetSettingsPublicConfigResponseEnvelope,
    summary="Retrieve widget config anonymously with domain verification and caching"
)
async def get_public_widget_config(
    company_id: UUID,
    request: Request,
    response: Response,
    origin: Optional[str] = Header(None, alias="Origin"),
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    service: WidgetService = Depends(get_widget_service)
):
    """
    Exposes styling and text layouts anonymously to the embedded script loader.
    Validates domain origins (CORS check) and returns a cacheable 304 response if matches ETag.
    """
    # 1. Enforce Domain Origin Whitelist Check
    # Verify origin is whitelisted (Origin is optionally provided by browser client)
    is_whitelisted = await service.verify_origin(company_id, origin)
    if not is_whitelisted:
        raise AuthorizationException("This domain origin is not whitelisted to load the widget")

    # Retrieve settings or create defaults anonymously
    import uuid as uuid_lib
    # Use Nil UUID for anonymous system default creation
    settings = await service.get_or_create_settings(company_id, uuid_lib.UUID(int=0))

    # 2. Map Public Response Layout
    public_config = WidgetSettingsPublicConfigResponse(
        theme_color=settings.theme_color,
        welcome_message=settings.welcome_message,
        bot_name=settings.bot_name,
        is_enabled=settings.is_enabled
    )
    envelope = WidgetSettingsPublicConfigResponseEnvelope(status="success", data=public_config)
    
    # 3. Calculate ETag Cache Validation
    json_bytes = json.dumps(envelope.model_dump(), default=str).encode("utf-8")
    etag = f'W/"{hashlib.sha1(json_bytes).hexdigest()}"'

    # Check ETag match
    if if_none_match == etag:
        response.status_code = status.HTTP_304_NOT_MODIFIED
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)

    # Set headers
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "public, max-age=3600"
    return envelope
