"""Tests for project and task endpoints."""
import pytest
from httpx import AsyncClient


async def make_project(client, headers, name="My Project"):
    resp = await client.post("/projects", json={"name": name}, headers=headers)
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_create_task_basic(client: AsyncClient, auth_headers):
    proj = await make_project(client, auth_headers)
    resp = await client.post(
        f"/projects/{proj['id']}/tasks",
        json={"title": "First task", "priority": "high"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    task = resp.json()
    assert task["title"] == "First task"
    assert task["status"] == "todo"  # default
    assert task["priority"] == "high"
    assert task["project_id"] == proj["id"]


@pytest.mark.asyncio
async def test_create_task_no_title_fails(client: AsyncClient, auth_headers):
    proj = await make_project(client, auth_headers)
    resp = await client.post(
        f"/projects/{proj['id']}/tasks",
        json={"priority": "low"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_task_status(client: AsyncClient, auth_headers):
    proj = await make_project(client, auth_headers)
    task_resp = await client.post(
        f"/projects/{proj['id']}/tasks",
        json={"title": "A task"},
        headers=auth_headers,
    )
    tid = task_resp.json()["id"]

    resp = await client.patch(f"/tasks/{tid}", json={"status": "in_progress"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_update_task_bad_status(client: AsyncClient, auth_headers):
    proj = await make_project(client, auth_headers)
    task = await client.post(
        f"/projects/{proj['id']}/tasks", json={"title": "Task"}, headers=auth_headers
    )
    tid = task.json()["id"]
    resp = await client.patch(f"/tasks/{tid}", json={"status": "invalid_status"}, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_filter_tasks_by_status(client: AsyncClient, auth_headers):
    proj = await make_project(client, auth_headers)
    pid = proj["id"]

    await client.post(f"/projects/{pid}/tasks", json={"title": "Todo task"}, headers=auth_headers)
    done = await client.post(f"/projects/{pid}/tasks", json={"title": "Done task"}, headers=auth_headers)
    await client.patch(f"/tasks/{done.json()['id']}", json={"status": "done"}, headers=auth_headers)

    resp = await client.get(f"/projects/{pid}/tasks?status=todo", headers=auth_headers)
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) >= 1
    assert all(t["status"] == "todo" for t in tasks)


@pytest.mark.asyncio
async def test_delete_task(client: AsyncClient, auth_headers):
    proj = await make_project(client, auth_headers)
    task = await client.post(
        f"/projects/{proj['id']}/tasks", json={"title": "Delete me"}, headers=auth_headers
    )
    tid = task.json()["id"]

    del_resp = await client.delete(f"/tasks/{tid}", headers=auth_headers)
    assert del_resp.status_code == 204

    # confirm it's actually gone
    list_resp = await client.get(f"/projects/{proj['id']}/tasks", headers=auth_headers)
    ids = [t["id"] for t in list_resp.json()]
    assert tid not in ids


@pytest.mark.asyncio
async def test_task_not_found(client: AsyncClient, auth_headers):
    fake_id = "00000000-0000-0000-0000-000000000099"
    resp = await client.patch(f"/tasks/{fake_id}", json={"title": "x"}, headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"] == "not found"


@pytest.mark.asyncio
async def test_create_multiple_projects(client: AsyncClient, auth_headers):
    await make_project(client, auth_headers, "Alpha")
    await make_project(client, auth_headers, "Beta")

    resp = await client.get("/projects", headers=auth_headers)
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert "Alpha" in names
    assert "Beta" in names


@pytest.mark.asyncio
async def test_project_stats_endpoint(client: AsyncClient, auth_headers):
    proj = await make_project(client, auth_headers, "Stats Test")
    pid = proj["id"]

    t1 = await client.post(f"/projects/{pid}/tasks", json={"title": "t1"}, headers=auth_headers)
    t2 = await client.post(f"/projects/{pid}/tasks", json={"title": "t2"}, headers=auth_headers)
    await client.patch(f"/tasks/{t2.json()['id']}", json={"status": "done"}, headers=auth_headers)

    resp = await client.get(f"/projects/{pid}/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "by_status" in body
    assert "by_assignee" in body

