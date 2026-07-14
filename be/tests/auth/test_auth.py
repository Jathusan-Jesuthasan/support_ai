import hashlib
import pytest
from uuid import UUID
from httpx import AsyncClient

from app.core.password import PasswordManager
from app.core.jwt import jwt_manager
from app.core.database import get_database
from app.shared.exceptions import ValidationException
from app.auth.model import TokenPurpose


@pytest.mark.asyncio
class TestPasswordManager:
    """
    Validates isolated PasswordManager complexity validation and Argon2id hashing.
    """

    async def test_password_complexity(self):
        pm = PasswordManager()
        
        # Too short
        with pytest.raises(ValidationException):
            pm.validate_password_strength("Short1!")

        # Missing uppercase
        with pytest.raises(ValidationException):
            pm.validate_password_strength("lowercase123!")

        # Missing lowercase
        with pytest.raises(ValidationException):
            pm.validate_password_strength("UPPERCASE123!")

        # Missing digits
        with pytest.raises(ValidationException):
            pm.validate_password_strength("NoDigitsHere!")

        # Missing special characters
        with pytest.raises(ValidationException):
            pm.validate_password_strength("ValidPassword123")

        # Perfectly valid password
        pm.validate_password_strength("SecurePassword123!")

    async def test_password_hashing(self):
        pm = PasswordManager()
        password = "SecurePassword123!"
        hashed = pm.hash_password(password)

        assert hashed != password
        assert pm.verify_password(password, hashed) is True
        assert pm.verify_password("WrongPassword123!", hashed) is False


@pytest.mark.asyncio
class TestJwtClaimsAndLifecycle:
    """
    Validates JWT claims conformance to RFC 7519 and JwtManager lifecycles.
    """

    async def test_access_token_claims(self):
        user_id = UUID("9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d")
        session_id = UUID("4a2c9b1d-8e6f-4d3a-9bdd-7b2d0c1e8f9a")
        token_version = 2

        token = jwt_manager.create_access_token(user_id, session_id, token_version)
        claims = jwt_manager.decode_token(token)

        assert claims["sub"] == f"usr_{user_id}"
        assert claims["uid"] == str(user_id)
        assert claims["sid"] == str(session_id)
        assert claims["tv"] == token_version
        assert "iss" in claims
        assert "aud" in claims
        assert "exp" in claims
        assert "iat" in claims
        assert "jti" in claims

    async def test_refresh_token_claims(self):
        user_id = UUID("9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d")
        session_id = UUID("4a2c9b1d-8e6f-4d3a-9bdd-7b2d0c1e8f9a")
        token_version = 2

        token = jwt_manager.create_refresh_token(user_id, session_id, token_version)
        claims = jwt_manager.decode_token(token, verify_aud_iss=False)

        assert claims["sub"] == f"usr_{user_id}"
        assert claims["uid"] == str(user_id)
        assert claims["sid"] == str(session_id)
        assert claims["tv"] == token_version
        assert "exp" in claims
        assert "iat" in claims
        assert "jti" in claims
        
        # Verify issuer and audience are not present in refresh token claims
        assert "iss" not in claims
        assert "aud" not in claims


@pytest.mark.asyncio
class TestAuthAPIIntegration:
    """
    Validates full end-to-end user lifecycles, logins, lockouts, email verification,
    and refresh token rotation via direct HTTP integration testing.
    """

    async def test_full_auth_flow(self, client: AsyncClient):
        db = get_database()

        # 1. Signup
        signup_payload = {
            "email": "integration@example.com",
            "password": "SecurePassword123!",
            "full_name": "Integration User"
        }
        res = await client.post("/api/v1/auth/signup", json=signup_payload)
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "success"
        assert data["data"]["email"] == "integration@example.com"
        assert data["data"]["is_email_verified"] is False

        # 2. Prevent Duplicate Signup
        res_dup = await client.post("/api/v1/auth/signup", json=signup_payload)
        assert res_dup.status_code == 409

        # 3. Retrieve Verification Token from DB
        token_doc = await db["verification_tokens"].find_one({"purpose": TokenPurpose.EMAIL_VERIFICATION.value})
        assert token_doc is not None

        # Verify email with mock verification token
        known_raw_token = "testverificationtoken"
        known_hash = hashlib.sha256(known_raw_token.encode()).hexdigest()
        await db["verification_tokens"].update_one(
            {"token_id": token_doc["token_id"]},
            {"$set": {"token_hash": known_hash}}
        )

        # Try to login BEFORE email verification (unverified user login check)
        login_payload = {
            "email": "integration@example.com",
            "password": "SecurePassword123!"
        }
        res_login_fail = await client.post("/api/v1/auth/login", json=login_payload)
        # Should fail authentication since user has is_active=False
        assert res_login_fail.status_code == 401

        # Verify Email
        res_verify = await client.get(f"/api/v1/auth/verify-email?token={known_raw_token}")
        assert res_verify.status_code == 200
        verify_data = res_verify.json()
        assert verify_data["status"] == "success"

        # Verify token used_at is set in DB
        updated_token = await db["verification_tokens"].find_one({"token_id": token_doc["token_id"]})
        assert updated_token["used_at"] is not None

        # Login AFTER email verification
        res_login = await client.post("/api/v1/auth/login", json=login_payload)
        assert res_login.status_code == 200
        login_data = res_login.json()
        assert login_data["status"] == "success"
        tokens = login_data["data"]
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        # 4. Get Me
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        res_me = await client.get("/api/v1/auth/me", headers=headers)
        assert res_me.status_code == 200
        me_data = res_me.json()
        assert me_data["status"] == "success"
        assert me_data["data"]["email"] == "integration@example.com"

        # 5. Token Rotation (RTR)
        refresh_payload = {"refresh_token": tokens["refresh_token"]}
        res_refresh = await client.post("/api/v1/auth/refresh", json=refresh_payload)
        assert res_refresh.status_code == 200
        refresh_data = res_refresh.json()
        new_tokens = refresh_data["data"]
        assert new_tokens["access_token"] != tokens["access_token"]
        assert new_tokens["refresh_token"] != tokens["refresh_token"]

        # 6. Replay Attack Detection
        # Submit the OLD refresh token again
        res_replay = await client.post("/api/v1/auth/refresh", json=refresh_payload)
        assert res_replay.status_code == 401
        
        # Verify all sessions are revoked for user
        user_doc = await db["users"].find_one({"email": "integration@example.com"})
        active_sessions_count = await db["sessions"].count_documents({
            "user_id": user_doc["user_id"],
            "is_revoked": False
        })
        assert active_sessions_count == 0
        assert user_doc["token_version"] > 1

        # Subsequent requests with rotated tokens fail because of replay-protection global revocation
        headers_new = {"Authorization": f"Bearer {new_tokens['access_token']}"}
        res_me_fail = await client.get("/api/v1/auth/me", headers=headers_new)
        assert res_me_fail.status_code == 401

    async def test_account_lockout(self, client: AsyncClient):
        # Signup and verify user
        signup_payload = {
            "email": "lockout@example.com",
            "password": "SecurePassword123!",
            "full_name": "Lockout User"
        }
        await client.post("/api/v1/auth/signup", json=signup_payload)
        db = get_database()
        await db["users"].update_one(
            {"email": "lockout@example.com"},
            {"$set": {"is_email_verified": True, "is_active": True}}
        )

        login_wrong_payload = {
            "email": "lockout@example.com",
            "password": "WrongPassword123!"
        }

        # Perform 5 failed logins
        for i in range(5):
            res = await client.post("/api/v1/auth/login", json=login_wrong_payload)
            assert res.status_code == 401

        # Check account is locked in DB and lock message is returned
        res_locked = await client.post("/api/v1/auth/login", json=login_wrong_payload)
        assert res_locked.status_code == 401
        assert "locked" in res_locked.json()["error"]["message"].lower()

        # Check in DB
        user = await db["users"].find_one({"email": "lockout@example.com"})
        assert user["failed_login_attempts"] >= 5
        assert user["locked_until"] is not None

    async def test_logout(self, client: AsyncClient):
        # Signup and verify user
        signup_payload = {
            "email": "logout@example.com",
            "password": "SecurePassword123!",
            "full_name": "Logout User"
        }
        await client.post("/api/v1/auth/signup", json=signup_payload)
        db = get_database()
        await db["users"].update_one(
            {"email": "logout@example.com"},
            {"$set": {"is_email_verified": True, "is_active": True}}
        )

        # Login
        login_payload = {
            "email": "logout@example.com",
            "password": "SecurePassword123!"
        }
        res_login = await client.post("/api/v1/auth/login", json=login_payload)
        tokens = res_login.json()["data"]

        # Logout
        logout_payload = {"refresh_token": tokens["refresh_token"]}
        res_logout = await client.post("/api/v1/auth/logout", json=logout_payload)
        assert res_logout.status_code == 200

        # Try to use refresh token after logout - should fail
        refresh_payload = {"refresh_token": tokens["refresh_token"]}
        res_refresh = await client.post("/api/v1/auth/refresh", json=refresh_payload)
        assert res_refresh.status_code == 401
