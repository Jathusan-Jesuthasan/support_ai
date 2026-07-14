from typing import Dict
from fastapi import APIRouter
from app.auth.router import router as auth_router
from app.company.router import router as company_router
from app.membership.router import router as membership_router
from app.knowledge.router import router as knowledge_router
from app.chat.router import router as chat_router, ws_router as chat_ws_router
from app.widget.router import admin_router as widget_admin_router, public_router as widget_public_router
from app.analytics.router import router as analytics_router

# Initialize the centralized V1 router
api_router = APIRouter()


# =====================================================================
# Temporary Infrastructure Endpoints
# =====================================================================


@api_router.get("/", summary="Root Status Endpoint")
async def read_root() -> Dict[str, str]:
    """
    Indicates that the SupportAI backend service is online.
    Used by ingress servers to verify route availability.
    """
    return {"message": "SupportAI Backend Running"}


@api_router.get("/health", summary="API Health Checker")
async def read_health() -> Dict[str, str]:
    """
    Calculates service status flags.
    Used by deployment cluster health checks (e.g. Kubernetes, ECS, PM2).
    """
    return {"status": "healthy", "version": "v1"}


# =====================================================================
# Future Feature Router Registrations (Placeholders)
# =====================================================================

# Once the corresponding feature directories and router modules are
# implemented in future sprints, uncomment these registrations.

# from app.chat.router import router as chat_router
# from app.widget.router import router as widget_router
# from app.analytics.router import router as analytics_router

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(company_router, prefix="/companies", tags=["Companies"])
api_router.include_router(membership_router, prefix="/membership", tags=["Memberships"])
api_router.include_router(knowledge_router, prefix="/companies/{company_id}/knowledge", tags=["Knowledge Base"])
api_router.include_router(chat_router, prefix="/companies/{company_id}", tags=["Conversations"])
api_router.include_router(chat_ws_router, prefix="/chat", tags=["Conversations (WebSockets)"])
api_router.include_router(widget_admin_router, prefix="/companies/{company_id}", tags=["Widget Settings"])
api_router.include_router(widget_public_router, prefix="/widget", tags=["Widget Settings (Public)"])
api_router.include_router(analytics_router, prefix="/companies/{company_id}", tags=["Analytics"])
