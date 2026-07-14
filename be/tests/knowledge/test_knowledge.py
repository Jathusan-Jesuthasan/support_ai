import pytest
import uuid
from httpx import AsyncClient
from app.core.enums import DocumentStatus
from app.core.database import get_database


@pytest.mark.asyncio
async def test_knowledge_and_parsing_flow(client: AsyncClient, tmp_path):
    db = get_database()

    # 1. Create and verify user
    email = "kb_owner@example.com"
    signup_resp = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "SecurePassword123!",
        "full_name": "KB Owner"
    })
    assert signup_resp.status_code == 201
    user_id = signup_resp.json()["data"]["user_id"]
    await db["users"].update_one(
        {"user_id": uuid.UUID(user_id)},
        {"$set": {"is_email_verified": True, "is_active": True}}
    )

    # Login
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "SecurePassword123!"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Company
    company_resp = await client.post(
        "/api/v1/companies",
        json={"name": "KB Corporation", "slug": "kb-corp"},
        headers=headers
    )
    assert company_resp.status_code == 201
    company_id = company_resp.json()["data"]["company_id"]
    headers["X-Company-ID"] = company_id

    # 3. Create Knowledge Reference
    create_resp = await client.post(
        f"/api/v1/companies/{company_id}/knowledge",
        json={"name": "Product Manual", "description": "Core product specifications", "source_type": "FILE_UPLOAD"},
        headers=headers
    )
    assert create_resp.status_code == 201
    knowledge_id = create_resp.json()["data"]["knowledge_id"]

    # 4. Upload File
    # Create a temporary txt file
    temp_file = tmp_path / "manual.txt"
    temp_file.write_text("Line 1: Product specifications. Line 2: Configuration settings. Line 3: API keys details.")

    with open(temp_file, "rb") as f:
        upload_resp = await client.post(
            f"/api/v1/companies/{company_id}/knowledge/{knowledge_id}/upload",
            files={"file": ("manual.txt", f, "text/plain")},
            headers=headers
        )
    assert upload_resp.status_code == 200
    assert upload_resp.json()["data"]["status"] in (DocumentStatus.PROCESSING.value, DocumentStatus.INDEXED.value)
    file_path = upload_resp.json()["data"]["file_url"]
    assert file_path is not None

    # 6. Retrieve status - should be INDEXED since Celery runs synchronously in eager mode
    status_resp = await client.get(
        f"/api/v1/companies/{company_id}/knowledge/{knowledge_id}",
        headers=headers
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["data"]["status"] == DocumentStatus.INDEXED.value
    assert status_resp.json()["data"]["current_version"] == 2 # Bumped from 1 because file_url is set

    # Verify chunks are created in DB
    chunks_count = await db["documents"].count_documents({"knowledge_id": uuid.UUID(knowledge_id)})
    assert chunks_count > 0

    # 7. List Knowledge
    list_resp = await client.get(
        f"/api/v1/companies/{company_id}/knowledge",
        headers=headers
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()["data"]) == 1

    # 8. Delete Knowledge
    delete_resp = await client.delete(
        f"/api/v1/companies/{company_id}/knowledge/{knowledge_id}",
        headers=headers
    )
    assert delete_resp.status_code == 200

    # Verify status is ARCHIVED (returns 404 due to is_deleted filter)
    status_resp2 = await client.get(
        f"/api/v1/companies/{company_id}/knowledge/{knowledge_id}",
        headers=headers
    )
    assert status_resp2.status_code == 404

    # Verify chunks are soft deleted
    deleted_chunks = await db["documents"].count_documents({
        "knowledge_id": uuid.UUID(knowledge_id),
        "is_deleted": True
    })
    assert deleted_chunks == chunks_count
