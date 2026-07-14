import pytest
import uuid
from httpx import AsyncClient
from app.core.database import get_database


@pytest.mark.asyncio
async def test_widget_admin_and_public_flows(client: AsyncClient):
    db = get_database()

    # 1. Create User & Login
    email = "widget_owner@example.com"
    signup_resp = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "SecurePassword123!",
        "full_name": "Widget Manager"
    })
    assert signup_resp.status_code == 201
    user_id = signup_resp.json()["data"]["user_id"]
    await db["users"].update_one(
        {"user_id": uuid.UUID(user_id)},
        {"$set": {"is_email_verified": True, "is_active": True}}
    )

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
        json={"name": "Widget Tech", "slug": "widget-tech"},
        headers=headers
    )
    assert company_resp.status_code == 201
    company_id = company_resp.json()["data"]["company_id"]
    headers["X-Company-ID"] = company_id

    # 3. Retrieve default settings as admin
    settings_resp = await client.get(
        f"/api/v1/companies/{company_id}/widget/settings",
        headers=headers
    )
    assert settings_resp.status_code == 200
    assert settings_resp.json()["data"]["theme_color"] == "#000000"

    # 4. Update allowed domains as admin (CORS restriction)
    update_resp = await client.put(
        f"/api/v1/companies/{company_id}/widget/settings",
        json={
            "theme_color": "#ff007f",
            "bot_name": "HelperBot",
            "allowed_domains": ["https://mytrustedsite.com", "http://localhost:3000"]
        },
        headers=headers
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["bot_name"] == "HelperBot"

    # 5. Fetch public config anonymously (Verify CORS blocks unauthorized domain)
    bad_origin_headers = {"Origin": "https://hackersite.com"}
    bad_pub_resp = await client.get(
        f"/api/v1/widget/{company_id}/config",
        headers=bad_origin_headers
    )
    assert bad_pub_resp.status_code == 403 # Forbidden due to origin check

    # 6. Fetch public config anonymously (Verify CORS whitelisted domain)
    good_origin_headers = {"Origin": "https://mytrustedsite.com"}
    good_pub_resp = await client.get(
        f"/api/v1/widget/{company_id}/config",
        headers=good_origin_headers
    )
    assert good_pub_resp.status_code == 200
    assert good_pub_resp.json()["data"]["bot_name"] == "HelperBot"
    etag_header = good_pub_resp.headers.get("ETag")
    assert etag_header is not None

    # 7. Check ETag Cache validation (returns 304 Not Modified)
    cache_headers = {
        "Origin": "https://mytrustedsite.com",
        "If-None-Match": etag_header
    }
    cached_resp = await client.get(
        f"/api/v1/widget/{company_id}/config",
        headers=cache_headers
    )
    assert cached_resp.status_code == 304
