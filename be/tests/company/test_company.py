import uuid
import pytest
from datetime import datetime, timezone
from uuid import UUID
from httpx import AsyncClient
from app.core.database import get_database
from app.core.enums import CompanyStatus, MembershipRole, MembershipStatus


async def create_verified_user(client: AsyncClient, email: str) -> str:
    """
    Helper function to register and verify a user, returning their access token.
    """
    db = get_database()
    
    # 1. Signup
    signup_payload = {
        "email": email,
        "password": "SecurePassword123!",
        "full_name": "Test User"
    }
    res = await client.post("/api/v1/auth/signup", json=signup_payload)
    assert res.status_code == 201
    
    # 2. Get user and activate
    await db["users"].update_one(
        {"email": email},
        {"$set": {"is_email_verified": True, "is_active": True}}
    )
    
    # 3. Login
    login_payload = {
        "email": email,
        "password": "SecurePassword123!"
    }
    res_login = await client.post("/api/v1/auth/login", json=login_payload)
    assert res_login.status_code == 200
    
    return res_login.json()["data"]["access_token"]


@pytest.mark.asyncio
class TestCompanyAPI:
    """
    Verifies CRUD company endpoints, slug autogeneration, soft-deletes, and RBAC role policies.
    """

    async def test_create_company_success(self, client: AsyncClient):
        db = get_database()
        token = await create_verified_user(client, "creator@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        payload = {
            "name": "Acme Corp",
            "slug": "acme-corp",
            "description": "Acme test company",
            "website": "https://acme.example.com",
            "industry": "Technology",
            "timezone": "America/New_York",
            "country": "US"
        }
        res = await client.post("/api/v1/companies", json=payload, headers=headers)
        assert res.status_code == 201
        
        data = res.json()["data"]
        company_id = UUID(data["company_id"])
        assert data["name"] == "Acme Corp"
        assert data["slug"] == "acme-corp"
        assert data["timezone"] == "America/New_York"
        assert data["country"] == "US"
        assert data["status"] == "ACTIVE"
        
        # Verify OWNER membership was automatically created for this user
        user = await db["users"].find_one({"email": "creator@example.com"})
        member = await db["company_members"].find_one({
            "user_id": user["user_id"],
            "company_id": company_id
        })
        assert member is not None
        assert member["role"] == MembershipRole.OWNER.value
        assert member["status"] == MembershipStatus.ACTIVE.value

    async def test_slug_autogeneration_and_conflict(self, client: AsyncClient):
        token = await create_verified_user(client, "slugger@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # 1. Create company without slug (should slugify the name)
        payload1 = {"name": "Acme Ltd"}
        res1 = await client.post("/api/v1/companies", json=payload1, headers=headers)
        assert res1.status_code == 201
        assert res1.json()["data"]["slug"] == "acme-ltd"

        # 2. Create another company with the same name (should suffix the slug)
        res2 = await client.post("/api/v1/companies", json=payload1, headers=headers)
        assert res2.status_code == 201
        assert res2.json()["data"]["slug"] == "acme-ltd-2"

        # 3. Create another company with duplicate explicit slug (should throw 409)
        payload_dup = {"name": "Another Acme", "slug": "acme-ltd"}
        res3 = await client.post("/api/v1/companies", json=payload_dup, headers=headers)
        assert res3.status_code == 409

    async def test_update_company_rbac(self, client: AsyncClient):
        db = get_database()
        
        # Create Owner and Admin users
        owner_token = await create_verified_user(client, "owner@example.com")
        admin_token = await create_verified_user(client, "admin@example.com")
        viewer_token = await create_verified_user(client, "viewer@example.com")
        non_member_token = await create_verified_user(client, "nonmember@example.com")
        
        # 1. Create company as Owner
        headers_owner = {"Authorization": f"Bearer {owner_token}"}
        res_create = await client.post("/api/v1/companies", json={"name": "Owner Company"}, headers=headers_owner)
        assert res_create.status_code == 201
        company_id_str = res_create.json()["data"]["company_id"]
        company_id = UUID(company_id_str)
        
        # Setup Admin and Viewer memberships in DB
        admin_user = await db["users"].find_one({"email": "admin@example.com"})
        await db["company_members"].insert_one({
            "membership_id": uuid.uuid4(),
            "company_id": company_id,
            "user_id": admin_user["user_id"],
            "role": MembershipRole.ADMIN.value,
            "status": MembershipStatus.ACTIVE.value,
            "is_deleted": False,
            "version": 1,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })

        viewer_user = await db["users"].find_one({"email": "viewer@example.com"})
        await db["company_members"].insert_one({
            "membership_id": uuid.uuid4(),
            "company_id": company_id,
            "user_id": viewer_user["user_id"],
            "role": MembershipRole.VIEWER.value,
            "status": MembershipStatus.ACTIVE.value,
            "is_deleted": False,
            "version": 1,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })

        # 2. Test Owner Update (allowed)
        update_payload = {"name": "Owner Updated Name"}
        res_update_owner = await client.put(f"/api/v1/companies/{company_id_str}", json=update_payload, headers=headers_owner)
        assert res_update_owner.status_code == 200
        assert res_update_owner.json()["data"]["name"] == "Owner Updated Name"

        # 3. Test Admin Update (allowed)
        headers_admin = {"Authorization": f"Bearer {admin_token}"}
        res_update_admin = await client.put(f"/api/v1/companies/{company_id_str}", json={"name": "Admin Updated Name"}, headers=headers_admin)
        assert res_update_admin.status_code == 200

        # 4. Test Viewer Update (Forbidden)
        headers_viewer = {"Authorization": f"Bearer {viewer_token}"}
        res_update_viewer = await client.put(f"/api/v1/companies/{company_id_str}", json={"name": "Viewer Change"}, headers=headers_viewer)
        assert res_update_viewer.status_code == 403

        # 5. Test Non-Member Update (Forbidden)
        headers_non_member = {"Authorization": f"Bearer {non_member_token}"}
        res_update_non = await client.put(f"/api/v1/companies/{company_id_str}", json={"name": "NonMember Change"}, headers=headers_non_member)
        assert res_update_non.status_code == 403

    async def test_soft_delete_company_rbac(self, client: AsyncClient):
        db = get_database()
        
        owner_token = await create_verified_user(client, "d_owner@example.com")
        admin_token = await create_verified_user(client, "d_admin@example.com")
        
        # 1. Create company as Owner
        headers_owner = {"Authorization": f"Bearer {owner_token}"}
        res_create = await client.post("/api/v1/companies", json={"name": "Delete Co"}, headers=headers_owner)
        company_id_str = res_create.json()["data"]["company_id"]
        company_id = UUID(company_id_str)
        
        # Add Admin member
        admin_user = await db["users"].find_one({"email": "d_admin@example.com"})
        await db["company_members"].insert_one({
            "membership_id": uuid.uuid4(),
            "company_id": company_id,
            "user_id": admin_user["user_id"],
            "role": MembershipRole.ADMIN.value,
            "status": MembershipStatus.ACTIVE.value,
            "is_deleted": False,
            "version": 1,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })

        # 2. Test Admin deletion (Forbidden - only Owner can delete)
        headers_admin = {"Authorization": f"Bearer {admin_token}"}
        res_del_admin = await client.delete(f"/api/v1/companies/{company_id_str}", headers=headers_admin)
        assert res_del_admin.status_code == 403

        # 3. Test Owner deletion (Allowed)
        res_del_owner = await client.delete(f"/api/v1/companies/{company_id_str}", headers=headers_owner)
        assert res_del_owner.status_code == 200
        
        # 4. Verify company is soft deleted & archived in DB
        company_doc = await db["companies"].find_one({"company_id": company_id})
        assert company_doc["is_deleted"] is True
        assert company_doc["status"] == CompanyStatus.ARCHIVED.value
        
        # 5. Verify all membership links are marked REMOVED & is_deleted=True
        member_docs = await db["company_members"].find({"company_id": company_id}).to_list(length=10)
        for m in member_docs:
            assert m["is_deleted"] is True
            assert m["status"] == MembershipStatus.REMOVED.value

    async def test_cursor_pagination(self, client: AsyncClient):
        token = await create_verified_user(client, "pager@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create 3 companies for the user
        for i in range(3):
            await client.post("/api/v1/companies", json={"name": f"Company {i}"}, headers=headers)
            
        # Get first page (limit=2)
        res_page1 = await client.get("/api/v1/companies?limit=2", headers=headers)
        assert res_page1.status_code == 200
        data1 = res_page1.json()
        assert len(data1["data"]) == 2
        assert data1["meta"]["has_more"] is True
        assert data1["meta"]["next_cursor"] is not None
        
        # Get second page using cursor
        cursor = data1["meta"]["next_cursor"]
        res_page2 = await client.get(f"/api/v1/companies?limit=2&cursor={cursor}", headers=headers)
        assert res_page2.status_code == 200
        data2 = res_page2.json()
        assert len(data2["data"]) == 1
        assert data2["meta"]["has_more"] is False
        assert data2["meta"]["next_cursor"] is None
