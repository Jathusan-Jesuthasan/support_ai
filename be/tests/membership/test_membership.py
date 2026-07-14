import pytest
import uuid
from httpx import AsyncClient
from app.core.enums import MembershipRole, MembershipStatus
from app.core.database import get_database


@pytest.mark.asyncio
async def test_complete_membership_flow(client: AsyncClient):
    db = get_database()

    # 1. Create Owner User
    owner_email = "owner_flow@example.com"
    owner_resp = await client.post("/api/v1/auth/signup", json={
        "email": owner_email,
        "password": "SecurePassword123!",
        "full_name": "Workspace Owner"
    })
    assert owner_resp.status_code == 201
    owner_id = owner_resp.json()["data"]["user_id"]
    await db["users"].update_one(
        {"user_id": uuid.UUID(owner_id)},
        {"$set": {"is_email_verified": True, "is_active": True}}
    )

    owner_login = await client.post("/api/v1/auth/login", json={
        "email": owner_email,
        "password": "SecurePassword123!"
    })
    assert owner_login.status_code == 200
    owner_token = owner_login.json()["data"]["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # 2. Create Company Workspace
    company_resp = await client.post(
        "/api/v1/companies",
        json={"name": "Enterprise Ltd", "slug": "enterprise-ltd"},
        headers=owner_headers
    )
    assert company_resp.status_code == 201
    company_id = company_resp.json()["data"]["company_id"]
    owner_headers["X-Company-ID"] = company_id

    # 3. Create User A (to be Admin) and User B (to be Member)
    user_a_email = "usera@example.com"
    signup_a = await client.post("/api/v1/auth/signup", json={
        "email": user_a_email,
        "password": "SecurePassword123!",
        "full_name": "User A"
    })
    assert signup_a.status_code == 201
    user_a_id = signup_a.json()["data"]["user_id"]
    await db["users"].update_one(
        {"user_id": uuid.UUID(user_a_id)},
        {"$set": {"is_email_verified": True, "is_active": True}}
    )

    user_b_email = "userb@example.com"
    signup_b = await client.post("/api/v1/auth/signup", json={
        "email": user_b_email,
        "password": "SecurePassword123!",
        "full_name": "User B"
    })
    assert signup_b.status_code == 201
    user_b_id = signup_b.json()["data"]["user_id"]
    await db["users"].update_one(
        {"user_id": uuid.UUID(user_b_id)},
        {"$set": {"is_email_verified": True, "is_active": True}}
    )

    # 4. Invite User A as ADMIN
    invite_a = await client.post(
        "/api/v1/membership/invite",
        json={"email": user_a_email, "role": MembershipRole.ADMIN.value},
        headers=owner_headers
    )
    assert invite_a.status_code == 201
    membership_a_id = invite_a.json()["data"]["membership_id"]

    # 5. Prevent Duplicate Invitation
    dup_invite = await client.post(
        "/api/v1/membership/invite",
        json={"email": user_a_email, "role": MembershipRole.MEMBER.value},
        headers=owner_headers
    )
    assert dup_invite.status_code == 409 # Conflict/Duplicate

    # 6. Reject Invitation as User B (but invite B first)
    invite_b = await client.post(
        "/api/v1/membership/invite",
        json={"email": user_b_email, "role": MembershipRole.MEMBER.value},
        headers=owner_headers
    )
    assert invite_b.status_code == 201

    login_b = await client.post("/api/v1/auth/login", json={
        "email": user_b_email,
        "password": "SecurePassword123!"
    })
    assert login_b.status_code == 200
    token_b = login_b.json()["data"]["access_token"]
    headers_b = {
        "Authorization": f"Bearer {token_b}",
        "X-Company-ID": company_id
    }

    reject_b = await client.post("/api/v1/membership/reject", headers=headers_b)
    assert reject_b.status_code == 200
    assert reject_b.json()["data"]["status"] == MembershipStatus.REMOVED.value

    # 7. Accept Invitation as User A
    login_a = await client.post("/api/v1/auth/login", json={
        "email": user_a_email,
        "password": "SecurePassword123!"
    })
    token_a = login_a.json()["data"]["access_token"]
    headers_a = {
        "Authorization": f"Bearer {token_a}",
        "X-Company-ID": company_id
    }
    accept_a = await client.post("/api/v1/membership/accept", headers=headers_a)
    assert accept_a.status_code == 200
    assert accept_a.json()["data"]["status"] == MembershipStatus.ACTIVE.value

    # 8. Retrieve specific membership record (GET /membership/{id})
    get_member_a = await client.get(f"/api/v1/membership/{membership_a_id}", headers=owner_headers)
    assert get_member_a.status_code == 200
    assert get_member_a.json()["data"]["role"] == MembershipRole.ADMIN.value

    # 9. Update Role of User A to MEMBER (PATCH /membership/{id}/role)
    patch_resp = await client.patch(
        f"/api/v1/membership/{membership_a_id}/role",
        json={"role": MembershipRole.MEMBER.value},
        headers=owner_headers
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["role"] == MembershipRole.MEMBER.value

    # 10. Prevent Demoting last Owner
    # Fetch Owner's membership ID
    owner_member_doc = await db["company_members"].find_one({
        "user_id": uuid.UUID(owner_id),
        "company_id": uuid.UUID(company_id)
    })
    assert owner_member_doc is not None
    owner_membership_id = str(owner_member_doc["membership_id"])

    # Demote Owner to MEMBER should fail
    failed_demote = await client.patch(
        f"/api/v1/membership/{owner_membership_id}/role",
        json={"role": MembershipRole.MEMBER.value},
        headers=owner_headers
    )
    assert failed_demote.status_code == 409 # Conflict/Duplicate

    # 11. Leave Company Validation
    # Owner tries to leave but is last owner, should fail
    failed_leave = await client.post("/api/v1/membership/leave", headers=owner_headers)
    assert failed_leave.status_code == 409 # Conflict

    # Promote User A back to ADMIN to prepare for transfer
    await client.patch(
        f"/api/v1/membership/{membership_a_id}/role",
        json={"role": MembershipRole.ADMIN.value},
        headers=owner_headers
    )
    # Promote User A to OWNER by database first to satisfy active state for transfer
    await db["company_members"].update_one(
        {"membership_id": uuid.UUID(membership_a_id)},
        {"$set": {"status": MembershipStatus.ACTIVE.value}}
    )

    # 12. Transfer Ownership to User A
    transfer_resp = await client.post(
        "/api/v1/membership/transfer-owner",
        json={"target_user_id": user_a_id},
        headers=owner_headers
    )
    assert transfer_resp.status_code == 200
    assert transfer_resp.json()["data"]["role"] == MembershipRole.OWNER.value

    # Validate that original Owner is now ADMIN
    orig_owner_check = await client.get(f"/api/v1/membership/{owner_membership_id}", headers=headers_a)
    assert orig_owner_check.status_code == 200
    assert orig_owner_check.json()["data"]["role"] == MembershipRole.ADMIN.value

    # 13. Original Owner Leaves Company (since they are now ADMIN and not last owner)
    leave_resp = await client.post("/api/v1/membership/leave", headers=owner_headers)
    assert leave_resp.status_code == 200

    # Verify original owner is soft-deleted
    verify_left = await client.get(f"/api/v1/membership/{owner_membership_id}", headers=headers_a)
    assert verify_left.status_code == 404
