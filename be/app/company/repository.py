import base64
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.core.enums import CompanyStatus, MembershipStatus
from app.company.model import Company, CompanyMember


# =====================================================================
# Cursor Pagination Helpers
# =====================================================================

def encode_cursor(created_at: datetime, business_id: UUID) -> str:
    """
    Encodes the created_at timestamp and unique UUID identifier into a base64 URL safe cursor token.
    """
    payload = {
        "created_at": created_at.isoformat(),
        "id": str(business_id)
    }
    json_bytes = json.dumps(payload).encode("utf-8")
    return base64.urlsafe_b64encode(json_bytes).decode("utf-8")


def decode_cursor(cursor_str: str) -> Tuple[datetime, UUID]:
    """
    Decodes the base64 URL safe cursor token back to original created_at and UUID parameters.
    """
    try:
        decoded_bytes = base64.urlsafe_b64decode(cursor_str.encode("utf-8"))
        payload = json.loads(decoded_bytes.decode("utf-8"))
        dt = datetime.fromisoformat(payload["created_at"])
        business_id = UUID(payload["id"])
        return dt, business_id
    except Exception as e:
        raise ValueError("Invalid cursor format") from e


# =====================================================================
# CompanyRepository
# =====================================================================

class CompanyRepository:
    """
    Data-access layer for the 'companies' collection in MongoDB.
    Enforces strict soft-delete filters, indexes, and optimistic locking.
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None) -> None:
        self._db = db

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._db or get_database()

    async def create(self, company: Company) -> Company:
        """
        Persists a new company document in MongoDB.
        """
        payload = company.to_mongo()
        await self.db["companies"].insert_one(payload)
        return company

    async def get_by_company_id(self, company_id: UUID, include_deleted: bool = False) -> Optional[Company]:
        """
        Retrieves a company by its unique company_id.
        """
        query: Dict[str, Any] = {"company_id": company_id}
        if not include_deleted:
            query["is_deleted"] = False

        data = await self.db["companies"].find_one(query)
        return Company.from_mongo(data) if data else None

    async def get_by_slug(self, slug: str, include_deleted: bool = False) -> Optional[Company]:
        """
        Retrieves a company by its unique lowercase URL slug.
        """
        query: Dict[str, Any] = {"slug": slug.strip().lower()}
        if not include_deleted:
            query["is_deleted"] = False

        data = await self.db["companies"].find_one(query)
        return Company.from_mongo(data) if data else None

    async def list(
        self,
        limit: int = 20,
        cursor: Optional[str] = None,
        include_deleted: bool = False
    ) -> Tuple[List[Company], Optional[str], bool]:
        """
        Returns a page of active companies sorted by created_at desc, company_id desc using cursor pagination.
        """
        query: Dict[str, Any] = {}
        if not include_deleted:
            query["is_deleted"] = False

        if cursor:
            try:
                last_created_at, last_id = decode_cursor(cursor)
                query["$or"] = [
                    {"created_at": {"$lt": last_created_at}},
                    {"created_at": last_created_at, "company_id": {"$lt": last_id}}
                ]
            except ValueError:
                # Fallback to empty filter if cursor is malformed
                pass

        # Query limit + 1 items to determine if has_more is true
        cursor_query = self.db["companies"].find(query).sort([("created_at", -1), ("company_id", -1)]).limit(limit + 1)
        raw_results = await cursor_query.to_list(length=limit + 1)
        results: List[Company] = []
        for r in raw_results:
            if r:
                c = Company.from_mongo(r)
                if c:
                    results.append(c)

        has_more = len(results) > limit
        if has_more:
            results.pop()  # remove the extra item
            last_item = results[-1]
            next_cursor = encode_cursor(last_item.created_at, last_item.company_id)
        else:
            next_cursor = None

        return results, next_cursor, has_more

    async def update(self, company: Company) -> Optional[Company]:
        """
        Updates an existing company document utilizing optimistic concurrency controls.
        """
        payload = company.to_mongo()
        payload.pop("_id", None)

        current_version = company.version or 1
        payload["version"] = current_version + 1

        company.update_audit(company.updated_by)
        payload["updated_at"] = company.updated_at

        result = await self.db["companies"].replace_one(
            {"company_id": company.company_id, "version": current_version},
            payload
        )

        if result.modified_count == 0:
            return None

        company.version = current_version + 1
        return company

    async def soft_delete(self, company_id: UUID, modifier_id: UUID) -> bool:
        """
        Flags a company document as logically deleted and updates status to ARCHIVED.
        """
        now = datetime.now(timezone.utc)
        result = await self.db["companies"].update_one(
            {"company_id": company_id, "is_deleted": False},
            {
                "$set": {
                    "is_deleted": True,
                    "deleted_at": now,
                    "status": CompanyStatus.ARCHIVED.value,
                    "updated_at": now,
                    "updated_by": modifier_id
                }
            }
        )
        return result.modified_count > 0

    async def exists_by_slug(self, slug: str) -> bool:
        """
        Asserts if any active company document is already using the slug.
        """
        count = await self.db["companies"].count_documents({
            "slug": slug.strip().lower(),
            "is_deleted": False
        })
        return count > 0

    async def count(self, include_deleted: bool = False) -> int:
        """
        Counts total number of documents in companies collection.
        """
        query: Dict[str, Any] = {}
        if not include_deleted:
            query["is_deleted"] = False
        return await self.db["companies"].count_documents(query)


# =====================================================================
# CompanyMemberRepository
# =====================================================================

class CompanyMemberRepository:
    """
    Data-access layer for the 'company_members' collection in MongoDB.
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None) -> None:
        self._db = db

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._db or get_database()

    async def create(self, member: CompanyMember) -> CompanyMember:
        """
        Persists a new membership document.
        """
        payload = member.to_mongo()
        await self.db["company_members"].insert_one(payload)
        return member

    async def get_by_membership_id(self, membership_id: UUID, include_deleted: bool = False) -> Optional[CompanyMember]:
        """
        Retrieves a membership document by its UUID.
        """
        query: Dict[str, Any] = {"membership_id": membership_id}
        if not include_deleted:
            query["is_deleted"] = False

        data = await self.db["company_members"].find_one(query)
        return CompanyMember.from_mongo(data) if data else None

    async def get_by_user_and_company(self, user_id: UUID, company_id: UUID, include_deleted: bool = False) -> Optional[CompanyMember]:
        """
        Retrieves a membership pointer matching user_id and company_id.
        """
        query: Dict[str, Any] = {
            "user_id": user_id,
            "company_id": company_id
        }
        if not include_deleted:
            query["is_deleted"] = False

        data = await self.db["company_members"].find_one(query)
        return CompanyMember.from_mongo(data) if data else None

    async def list_company_members(
        self,
        company_id: UUID,
        limit: int = 20,
        cursor: Optional[str] = None,
        include_deleted: bool = False
    ) -> Tuple[List[CompanyMember], Optional[str], bool]:
        """
        Returns a paginated list of memberships inside a company.
        """
        query: Dict[str, Any] = {"company_id": company_id}
        if not include_deleted:
            query["is_deleted"] = False

        if cursor:
            try:
                last_created_at, last_id = decode_cursor(cursor)
                query["$or"] = [
                    {"created_at": {"$lt": last_created_at}},
                    {"created_at": last_created_at, "membership_id": {"$lt": last_id}}
                ]
            except ValueError:
                pass

        cursor_query = self.db["company_members"].find(query).sort([("created_at", -1), ("membership_id", -1)]).limit(limit + 1)
        raw_results = await cursor_query.to_list(length=limit + 1)
        results: List[CompanyMember] = []
        for r in raw_results:
            if r:
                m = CompanyMember.from_mongo(r)
                if m:
                    results.append(m)

        has_more = len(results) > limit
        if has_more:
            results.pop()
            last_item = results[-1]
            next_cursor = encode_cursor(last_item.created_at, last_item.membership_id)
        else:
            next_cursor = None

        return results, next_cursor, has_more

    async def list_user_companies(
        self,
        user_id: UUID,
        limit: int = 20,
        cursor: Optional[str] = None,
        include_deleted: bool = False
    ) -> Tuple[List[CompanyMember], Optional[str], bool]:
        """
        Returns a paginated list of memberships held by a user across companies.
        """
        query: Dict[str, Any] = {"user_id": user_id}
        if not include_deleted:
            query["is_deleted"] = False

        if cursor:
            try:
                last_created_at, last_id = decode_cursor(cursor)
                query["$or"] = [
                    {"created_at": {"$lt": last_created_at}},
                    {"created_at": last_created_at, "membership_id": {"$lt": last_id}}
                ]
            except ValueError:
                pass

        cursor_query = self.db["company_members"].find(query).sort([("created_at", -1), ("membership_id", -1)]).limit(limit + 1)
        raw_results = await cursor_query.to_list(length=limit + 1)
        results: List[CompanyMember] = []
        for r in raw_results:
            if r:
                m = CompanyMember.from_mongo(r)
                if m:
                    results.append(m)

        has_more = len(results) > limit
        if has_more:
            results.pop()
            last_item = results[-1]
            next_cursor = encode_cursor(last_item.created_at, last_item.membership_id)
        else:
            next_cursor = None

        return results, next_cursor, has_more

    async def update(self, member: CompanyMember) -> Optional[CompanyMember]:
        """
        Updates an existing membership document using optimistic concurrency version control.
        """
        payload = member.to_mongo()
        payload.pop("_id", None)

        current_version = member.version or 1
        payload["version"] = current_version + 1

        member.update_audit(member.updated_by)
        payload["updated_at"] = member.updated_at

        result = await self.db["company_members"].replace_one(
            {"membership_id": member.membership_id, "version": current_version},
            payload
        )

        if result.modified_count == 0:
            return None

        member.version = current_version + 1
        return member

    async def soft_delete(self, membership_id: UUID, modifier_id: UUID) -> bool:
        """
        Flags a user membership as logically deleted and updates status to REMOVED.
        """
        now = datetime.now(timezone.utc)
        result = await self.db["company_members"].update_one(
            {"membership_id": membership_id, "is_deleted": False},
            {
                "$set": {
                    "is_deleted": True,
                    "deleted_at": now,
                    "status": MembershipStatus.REMOVED.value,
                    "updated_at": now,
                    "updated_by": modifier_id
                }
            }
        )
        return result.modified_count > 0

    async def remove_all_company_members(self, company_id: UUID, modifier_id: UUID) -> int:
        """
        Flags all active memberships of a company as logically deleted.
        """
        now = datetime.now(timezone.utc)
        result = await self.db["company_members"].update_many(
            {"company_id": company_id, "is_deleted": False},
            {
                "$set": {
                    "is_deleted": True,
                    "deleted_at": now,
                    "status": MembershipStatus.REMOVED.value,
                    "updated_at": now,
                    "updated_by": modifier_id
                }
            }
        )
        return result.modified_count
