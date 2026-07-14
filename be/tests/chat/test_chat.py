import pytest
import uuid
from httpx import AsyncClient
from app.core.enums import ConversationStatus
from app.core.database import get_database


@pytest.mark.asyncio
async def test_chat_engine_rest_and_websocket_flows(client: AsyncClient):
    db = get_database()

    # 1. Create and verify user
    email = "chat_user@example.com"
    signup_resp = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "SecurePassword123!",
        "full_name": "Chat Agent"
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
        json={"name": "Chat Inc", "slug": "chat-inc"},
        headers=headers
    )
    assert company_resp.status_code == 201
    company_id = company_resp.json()["data"]["company_id"]
    headers["X-Company-ID"] = company_id

    # 3. Create Conversation
    conv_resp = await client.post(
        f"/api/v1/companies/{company_id}/conversations",
        json={"user_identifier": "test_guest_cookie"},
        headers=headers
    )
    assert conv_resp.status_code == 201
    conversation_id = conv_resp.json()["data"]["conversation_id"]

    # 4. List Conversations
    list_conv = await client.get(
        f"/api/v1/companies/{company_id}/conversations",
        headers=headers
    )
    assert list_conv.status_code == 200
    assert len(list_conv.json()["data"]) == 1

    # 5. Create a Product to query in catalog
    prod_resp = await client.post(
        f"/api/v1/companies/{company_id}/products",
        json={
            "sku": "PROD-100",
            "name": "SuperWidget",
            "description": "High performance widget",
            "price": 29.99,
            "url": "http://example.com/widget",
            "is_available": True
        },
        headers=headers
    )
    assert prod_resp.status_code == 201
    assert "product_id" in prod_resp.json()["data"]

    # Search Product
    search_resp = await client.get(
        f"/api/v1/companies/{company_id}/products/search?q=SuperWidget",
        headers=headers
    )
    assert search_resp.status_code == 200
    assert len(search_resp.json()["data"]) == 1
    assert search_resp.json()["data"][0]["sku"] == "PROD-100"

    # 6. Send user message via REST endpoint (triggers RAG in fallback/mock mode)
    msg_resp = await client.post(
        f"/api/v1/companies/{company_id}/conversations/{conversation_id}/messages",
        json={"content": "Do you sell SuperWidgets?"},
        headers=headers
    )
    assert msg_resp.status_code == 201
    assistant_reply = msg_resp.json()["data"]["content"]
    message_id = msg_resp.json()["data"]["message_id"]
    assert assistant_reply is not None

    # 7. Submit Feedback Rating
    feedback_resp = await client.post(
        f"/api/v1/companies/{company_id}/conversations/{conversation_id}/messages/{message_id}/feedback",
        json={"score": 1},
        headers=headers
    )
    assert feedback_resp.status_code == 200
    assert feedback_resp.json()["data"]["feedback_score"] == 1

    # 8. List Messages (Paginated)
    list_msg = await client.get(
        f"/api/v1/companies/{company_id}/conversations/{conversation_id}/messages",
        headers=headers
    )
    assert list_msg.status_code == 200
    # Should contain at least the user message and the assistant reply
    assert len(list_msg.json()["data"]) >= 2

    # 9. Update Status
    status_resp = await client.patch(
        f"/api/v1/companies/{company_id}/conversations/{conversation_id}/status",
        json={"status": ConversationStatus.CLOSED.value},
        headers=headers
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["data"]["status"] == ConversationStatus.CLOSED.value

    # 10. WebSocket Streaming Test
    # We will use the test client websocket hook to connect
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as sync_client:
        ws_url = f"/api/v1/chat/ws?token=DummyTokenForTesting&company_id={company_id}&conversation_id={conversation_id}"
        with sync_client.websocket_connect(ws_url) as ws:
            # Send prompt
            ws.send_text("Hello stream chatbot!")
            
            # Receive token streams
            tokens = []
            while True:
                msg_data = ws.receive_json()
                event = msg_data.get("event")
                if event == "message.token":
                    tokens.append(msg_data["payload"]["token"])
                elif event == "message.completed":
                    # Final result received
                    assert msg_data["payload"]["content"] is not None
                    break
            
            assert len(tokens) > 0
