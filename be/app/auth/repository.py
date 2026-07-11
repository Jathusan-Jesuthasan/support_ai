from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.auth.model import User, VerificationToken, Session, TokenPurpose
from app.core.database import get_database


class UserRepository:
    """
    Data-access layer for the 'users' collection in MongoDB.
    Performs only raw database queries.
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None) -> None:
        self._db = db

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._db or get_database()

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Retrieves a user document by their unique business UUID.
        """
        data = await self.db["users"].find_one({"user_id": user_id})
        return User.from_mongo(data) if data else None

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Retrieves a user document by email.
        """
        data = await self.db["users"].find_one({"email": email.strip().lower()})
        return User.from_mongo(data) if data else None

    async def create(self, user: User) -> User:
        """
        Persists a new user document in the database.
        """
        payload = user.to_mongo()
        await self.db["users"].insert_one(payload)
        return user

    async def update(self, user: User) -> User:
        """
        Updates an existing user document.
        """
        payload = user.to_mongo()
        payload.pop("_id", None)
        # Ensure we filter by user_id UUID
        await self.db["users"].replace_one({"user_id": user.user_id}, payload)
        return user


class VerificationTokenRepository:
    """
    Data-access layer for the 'verification_tokens' collection.
    Performs only raw database queries.
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None) -> None:
        self._db = db

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._db or get_database()

    async def get_by_hash(self, token_hash: str, purpose: TokenPurpose) -> Optional[VerificationToken]:
        """
        Retrieves a verification token document by its token hash and purpose.
        """
        data = await self.db["verification_tokens"].find_one({
            "token_hash": token_hash,
            "purpose": purpose.value
        })
        return VerificationToken.from_mongo(data) if data else None

    async def create(self, token: VerificationToken) -> VerificationToken:
        """
        Persists a new verification token document.
        """
        payload = token.to_mongo()
        await self.db["verification_tokens"].insert_one(payload)
        return token

    async def update(self, token: VerificationToken) -> VerificationToken:
        """
        Updates an existing verification token document.
        """
        payload = token.to_mongo()
        payload.pop("_id", None)
        await self.db["verification_tokens"].replace_one({"token_id": token.token_id}, payload)
        return token


class SessionRepository:
    """
    Data-access layer for the 'sessions' collection in MongoDB.
    Performs only raw database queries.
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None) -> None:
        self._db = db

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._db or get_database()

    async def get_by_id(self, session_id: UUID) -> Optional[Session]:
        """
        Retrieves a session document by its unique UUID.
        """
        data = await self.db["sessions"].find_one({"session_id": session_id})
        return Session.from_mongo(data) if data else None

    async def get_by_hash(self, refresh_token_hash: str) -> Optional[Session]:
        """
        Retrieves a session document by the hash of its refresh token.
        """
        data = await self.db["sessions"].find_one({"refresh_token_hash": refresh_token_hash})
        return Session.from_mongo(data) if data else None

    async def create(self, session: Session) -> Session:
        """
        Persists a new session document.
        """
        payload = session.to_mongo()
        await self.db["sessions"].insert_one(payload)
        return session

    async def update(self, session: Session) -> Session:
        """
        Updates an existing session document.
        """
        payload = session.to_mongo()
        payload.pop("_id", None)
        await self.db["sessions"].replace_one({"session_id": session.session_id}, payload)
        return session


    async def revoke_by_id(self, session_id: UUID) -> None:
        """
        Revokes a session by setting is_revoked to True and updating audit fields.
        """
        now = datetime.now(timezone.utc)
        await self.db["sessions"].update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "is_revoked": True,
                    "updated_at": now
                }
            }
        )

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        """
        Revokes all active sessions for a user.
        """
        now = datetime.now(timezone.utc)
        await self.db["sessions"].update_many(
            {"user_id": user_id, "is_revoked": False},
            {
                "$set": {
                    "is_revoked": True,
                    "updated_at": now
                }
            }
        )
