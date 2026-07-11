import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import db_manager, get_database

@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_test_db():
    # Establish connection to test database
    await db_manager.connect()
    db = get_database()
    # Clean database before tests run
    await db["users"].delete_many({})
    await db["sessions"].delete_many({})
    await db["verification_tokens"].delete_many({})
    
    yield
    
    # Clean database after session finishes
    db = get_database()
    await db["users"].delete_many({})
    await db["sessions"].delete_many({})
    await db["verification_tokens"].delete_many({})
    db_manager.disconnect()

@pytest_asyncio.fixture(loop_scope="session", autouse=True)
async def clean_collections():
    # Clean collections between test cases to prevent cross-contamination
    db = get_database()
    await db["users"].delete_many({})
    await db["sessions"].delete_many({})
    await db["verification_tokens"].delete_many({})

@pytest_asyncio.fixture(scope="session")
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://127.0.0.1:8001"
    ) as ac:
        yield ac
