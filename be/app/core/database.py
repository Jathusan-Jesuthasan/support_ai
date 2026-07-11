import asyncio
import logging
from typing import Any, Dict
# pyrefly: ignore [missing-import]
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import get_settings

logger = logging.getLogger("supportai.database")


class DatabaseManager:

    """
    Manages the lifecycle of connection pools to the MongoDB Atlas cluster.
    Performs async startup verifications and provides transaction session builders.
    """

    def __init__(self) -> None:
        self.client: AsyncIOMotorClient | None = None
        self.db: AsyncIOMotorDatabase | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def get_db(self) -> AsyncIOMotorDatabase:
        """
        Returns the database reference for the current event loop context.
        Re-initializes the Motor client if the event loop changes (common in tests).
        """
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self.client is None or (current_loop is not None and self._loop is not current_loop):
            settings = get_settings()
            logger.info("Initializing/Re-binding MongoDB Atlas client for current event loop...")
            self.client = AsyncIOMotorClient(
                str(settings.MONGODB_URI),
                maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
                minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
                maxIdleTimeMS=settings.MONGODB_MAX_IDLE_TIME_MS,
                serverSelectionTimeoutMS=5000,
                uuidRepresentation="standard"
            )

            self.db = self.client[settings.MONGODB_DB_NAME]
            self._loop = current_loop

        return self.db

    async def connect(self) -> None:
        """
        Asynchronously initializes the Motor client and runs a connection ping test.
        Enforces connection pool settings loaded from environment config.
        """
        # Triggers self.get_db() to initialize client on current loop
        self.get_db()


        # Verify connectivity using administrative ping command
        if self.client is None:
            raise RuntimeError("Database connection not initialized.")
        try:
            await self.client.admin.command("ping")

            logger.info("Successfully pinged MongoDB Atlas. Connection pool healthy.")
        except Exception as e:
            logger.critical(f"Failed to connect to MongoDB Atlas: {e}")
            self.disconnect()
            raise e

        # Trigger index builds
        await self.initialize_indexes()

    def disconnect(self) -> None:
        """
        Closes active database socket pools cleanly.
        Called during ASGI system shutdown.
        """
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            self._loop = None
            logger.info("MongoDB Atlas connection pool closed.")

    async def health_check(self) -> Dict[str, Any]:
        """
        Checks connection status to the cluster.
        Utilized by health check API endpoints.
        """
        self.get_db()
        if not self.client:

            return {"status": "unhealthy", "error": "Database client is not initialized"}
        try:
            await self.client.admin.command("ping")
            return {"status": "healthy", "connected": True}
        except Exception as e:
            logger.error(f"MongoDB health check ping failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    async def initialize_indexes(self) -> None:
        """
        Generates indexes, unique constraints, and TTL policies on application start.
        """
        from pymongo import ASCENDING
        from pymongo.collation import Collation

        logger.info("Verifying database indexes and unique constraints...")
        
        db = self.get_db()
        if db is None:
            logger.error("Database connection not initialized. Skipping index creation.")
            return

        try:
            # 1. users Indexes
            await db["users"].create_index("user_id", unique=True)
            await db["users"].create_index(
                "email",
                unique=True,
                collation=Collation(locale="en", strength=2)
            )
            await db["users"].create_index([("is_deleted", ASCENDING), ("is_active", ASCENDING)])
            logger.info("Database indexes for 'users' collection initialized successfully.")

            # 2. sessions Indexes
            await db["sessions"].create_index("session_id", unique=True)
            await db["sessions"].create_index("user_id")
            await db["sessions"].create_index("expires_at", expireAfterSeconds=0)
            logger.info("Database indexes for 'sessions' collection initialized successfully.")

            # 3. verification_tokens Indexes
            await db["verification_tokens"].create_index("token_id", unique=True)
            await db["verification_tokens"].create_index([("token_hash", ASCENDING), ("purpose", ASCENDING)])
            await db["verification_tokens"].create_index("expires_at", expireAfterSeconds=0)
            logger.info("Database indexes for 'verification_tokens' collection initialized successfully.")
        except Exception as e:
            logger.error(f"Error occurred while initializing database indexes: {e}")

    async def start_session(self) -> Any:
        """
        Acquires an asynchronous transaction session context.
        Provides support for multi-document ACID transactions across collections.
        """
        self.get_db()
        if not self.client:
            raise RuntimeError("Database connection not initialized.")
        return await self.client.start_session()



# Singleton manager instance exposed for application lifecycle hooks
db_manager = DatabaseManager()


def get_database() -> AsyncIOMotorDatabase:
    """
    Dependency provider returning the active database reference.
    Guarantees that database calls are routed through the managed connection pool.
    """
    return db_manager.get_db()

