import pytest
import uuid
from httpx import AsyncClient
from app.core.database import get_database


@pytest.mark.asyncio
async def test_analytics_metrics_and_event_streams(client: AsyncClient):
    db = get_database()

    # 1. Create and verify user
    email = "analyst@example.com"
    signup_resp = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "SecurePassword123!",
        "full_name": "Data Analyst"
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
        json={"name": "Analytics Inc", "slug": "analytics-inc"},
        headers=headers
    )
    assert company_resp.status_code == 201
    company_id = company_resp.json()["data"]["company_id"]
    headers["X-Company-ID"] = company_id

    # 3. Create Conversation, Message, and Feedback to populate counts in database
    conv_resp = await client.post(
        f"/api/v1/companies/{company_id}/conversations",
        json={"user_identifier": "guest_analyst"},
        headers=headers
    )
    assert conv_resp.status_code == 201
    conversation_id = conv_resp.json()["data"]["conversation_id"]

    # Send message (triggers MESSAGE_SENT event logging under the hood)
    msg_resp = await client.post(
        f"/api/v1/companies/{company_id}/conversations/{conversation_id}/messages",
        json={"content": "Log me an event!"},
        headers=headers
    )
    assert msg_resp.status_code == 201
    message_id = msg_resp.json()["data"]["message_id"]

    # Submit feedback rating (triggers HELP_HELPFUL event logging under the hood)
    feedback_resp = await client.post(
        f"/api/v1/companies/{company_id}/conversations/{conversation_id}/messages/{message_id}/feedback",
        json={"score": 1},
        headers=headers
    )
    assert feedback_resp.status_code == 200

    # 4. Fetch dashboard stats as admin
    dashboard_resp = await client.get(
        f"/api/v1/companies/{company_id}/analytics/dashboard",
        headers=headers
    )
    assert dashboard_resp.status_code == 200
    data = dashboard_resp.json()["data"]
    assert data["total_conversations"] == 1
    assert data["total_messages"] >= 1
    assert data["helpful_ratings"] == 1
    assert data["unhelpful_ratings"] == 0

    # 5. Fetch cursor-paginated event logs list stream
    events_resp = await client.get(
        f"/api/v1/companies/{company_id}/analytics/events?limit=10",
        headers=headers
    )
    assert events_resp.status_code == 200
    assert len(events_resp.json()["data"]) >= 2  # MESSAGE_SENT + HELP_HELPFUL events
