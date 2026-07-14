import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse
from uuid import UUID

from app.shared.exceptions import NotFoundException, ConflictException
from app.company.repository import CompanyRepository
from app.widget.model import WidgetSettings
from app.widget.schema import WidgetSettingsUpdateRequest
from app.widget.repository import WidgetRepository

logger = logging.getLogger("supportai.widget.service")


class WidgetService:
    """
    Coordinates widget settings retrieval, configuration updates, and CORS whitelist check validations.
    """

    def __init__(
        self,
        widget_repo: Optional[WidgetRepository] = None,
        company_repo: Optional[CompanyRepository] = None
    ) -> None:
        self.widget_repo = widget_repo or WidgetRepository()
        self.company_repo = company_repo or CompanyRepository()

    async def get_or_create_settings(self, company_id: UUID, creator_id: UUID) -> WidgetSettings:
        """
        Retrieves existing widget settings for a company, or builds default configuration.
        """
        company = await self.company_repo.get_by_company_id(company_id)
        if not company:
            raise NotFoundException("Company workspace not found")

        settings = await self.widget_repo.get_by_company_id(company_id)
        if settings:
            return settings

        # Create defaults
        now = datetime.now(timezone.utc)
        settings = WidgetSettings(
            widget_id=uuid.uuid4(),
            company_id=company_id,
            theme_color="#000000",
            welcome_message="Hello! How can we help you today?",
            bot_name="SupportBot",
            allowed_domains=["*"]  # Open by default, can be restricted by admins
        )
        settings.created_at = now
        settings.updated_at = now
        settings.created_by = creator_id
        settings.updated_by = creator_id
        return await self.widget_repo.create(settings)

    async def update_settings(
        self,
        company_id: UUID,
        payload: WidgetSettingsUpdateRequest,
        modifier_id: UUID
    ) -> WidgetSettings:
        """
        Updates theme appearance or CORS whitelists.
        """
        settings = await self.get_or_create_settings(company_id, modifier_id)

        if payload.theme_color is not None:
            settings.theme_color = payload.theme_color
        if payload.welcome_message is not None:
            settings.welcome_message = payload.welcome_message
        if payload.bot_name is not None:
            settings.bot_name = payload.bot_name
        if payload.allowed_domains is not None:
            settings.allowed_domains = payload.allowed_domains
        if payload.is_enabled is not None:
            settings.is_enabled = payload.is_enabled

        settings.updated_at = datetime.now(timezone.utc)
        settings.updated_by = modifier_id

        updated = await self.widget_repo.update(settings)
        if not updated:
            raise ConflictException("Failed to update widget settings due to resource collision")
        return updated

    async def verify_origin(self, company_id: UUID, origin_url: Optional[str]) -> bool:
        """
        Validates request origin header against the allowed domains config whitelist.
        """
        settings = await self.widget_repo.get_by_company_id(company_id)
        if not settings or not settings.is_enabled:
            return False

        # If allowed domains contains wildcard '*', anyone is allowed
        if "*" in settings.allowed_domains:
            return True

        if not origin_url:
            # If origin is missing and allowed domains are restricted, reject it
            return False

        # Parse hostname/origin domain
        try:
            parsed = urlparse(origin_url)
            # Match scheme + netloc or netloc itself (e.g. localhost:3000 or example.com)
            origin_netloc = parsed.netloc.lower()
            origin_host = parsed.hostname.lower() if parsed.hostname else ""

            for allowed in settings.allowed_domains:
                allowed_lower = allowed.strip().lower()
                # Check for direct matching
                if allowed_lower == origin_url.lower():
                    return True
                # Check hostname / host matching
                parsed_allowed = urlparse(allowed_lower)
                allowed_netloc = parsed_allowed.netloc.lower() if parsed_allowed.netloc else allowed_lower
                if allowed_netloc == origin_netloc or allowed_netloc == origin_host:
                    return True
        except Exception:
            logger.warning(f"Error parsing origin URL: {origin_url}")
            return False

        return False
