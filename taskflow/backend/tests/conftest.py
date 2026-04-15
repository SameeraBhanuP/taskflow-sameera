"""
Integration test fixtures.
Requires a running PostgreSQL instance — set TEST_DATABASE_URL in your environment.
These tests are meant to run against a test database, not production.
"""
import asyncio
import os
import pytest
import asyncpg
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Point at a dedicated test DB
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://taskflow:taskflow_secret@localhost:5432/taskflow_test",
)

# Override config before importing the app
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["JWT_SECRET"] = "test-secret-key-for-tests-only"
os.environ["ENVIRONMENT"] = "test"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_pool():
    pool = await asyncpg.create_pool(dsn=TEST_DATABASE_URL.replace("postgresql://", "postgres://"))
    yield pool
    await pool.close()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(db_pool):
    """Wipe tables before each test for isolation."""
    async with db_pool.acquire() as conn:
        await conn.execute("TRUNCATE users, projects, tasks RESTART IDENTITY CASCADE")
    yield


@pytest_asyncio.fixture
async def client():
    from app.main import app
    app.state.pool = await asyncpg.create_pool(
        dsn=TEST_DATABASE_URL.replace("postgresql://", "postgres://")
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await app.state.pool.close()


@pytest_asyncio.fixture
async def auth_headers(client):
    """Register a user and return auth headers."""
    resp = await client.post("/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123",
    })
    assert resp.status_code == 201
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}
