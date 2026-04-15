"""Tests for /auth endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_returns_token(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "name": "Jane Doe",
        "email": "jane@example.com",
        "password": "securepass123",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert "token" in body
    assert body["user"]["email"] == "jane@example.com"
    # make sure we're not leaking the password back
    assert "password" not in body["user"]


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_400(client: AsyncClient):
    payload = {"name": "Jane", "email": "jane@example.com", "password": "pass1234"}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 400
    assert resp.json()["error"] == "validation failed"


@pytest.mark.asyncio
async def test_register_short_password_fails(client: AsyncClient):
    # password min length is 8
    resp = await client.post("/auth/register", json={
        "name": "Bob", "email": "bob@example.com", "password": "short"
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_works(client: AsyncClient):
    await client.post("/auth/register", json={
        "name": "Jane", "email": "jane@example.com", "password": "securepass123"
    })
    resp = await client.post("/auth/login", json={
        "email": "jane@example.com", "password": "securepass123"
    })
    assert resp.status_code == 200
    assert "token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/auth/register", json={
        "name": "Jane", "email": "jane@example.com", "password": "correct-pass"
    })
    resp = await client.post("/auth/login", json={
        "email": "jane@example.com", "password": "wrong-pass"
    })
    assert resp.status_code == 401
    assert resp.json()["error"] == "unauthorized"


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient):
    resp = await client.post("/auth/login", json={
        "email": "nobody@example.com", "password": "whatever123"
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_no_token_gets_rejected(client: AsyncClient):
    resp = await client.get("/projects")
    # HTTPBearer returns 403 when no credentials at all
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_bad_token_gets_rejected(client: AsyncClient):
    resp = await client.get("/projects", headers={"Authorization": "Bearer not.a.real.token"})
    assert resp.status_code == 401

