import logging
from typing import List, Optional
from uuid import UUID

import asyncpg
from fastapi import HTTPException

from app.schemas.schemas import TaskCreate, TaskOut, TaskStatus, TaskUpdate

logger = logging.getLogger(__name__)


async def list_tasks(
    project_id: UUID,
    user_id: UUID,
    db: asyncpg.Connection,
    status: Optional[TaskStatus] = None,
    assignee_id: Optional[UUID] = None,
    page: int = 1,
    limit: int = 50,
) -> List[TaskOut]:
    await _check_project_exists(project_id, db)

    conditions = ["project_id = $1"]
    params: list = [project_id]
    idx = 2

    if status:
        conditions.append(f"status = ${idx}::task_status")
        params.append(status.value)
        idx += 1
    if assignee_id:
        conditions.append(f"assignee_id = ${idx}")
        params.append(assignee_id)
        idx += 1

    offset = (page - 1) * limit
    where_clause = " AND ".join(conditions)

    rows = await db.fetch(
        f"SELECT id, title, description, status, priority, project_id, "
        f"assignee_id, due_date, created_at, updated_at "
        f"FROM tasks WHERE {where_clause} ORDER BY created_at DESC "
        f"LIMIT ${idx} OFFSET ${idx+1}",
        *params, limit, offset,
    )
    return [TaskOut(**dict(r)) for r in rows]


async def create_task(
    project_id: UUID, req: TaskCreate, user_id: UUID, db: asyncpg.Connection
) -> TaskOut:
    await _check_project_exists(project_id, db)

    if req.assignee_id:
        await _check_user_exists(req.assignee_id, db)

    result = await db.fetchrow(
        "INSERT INTO tasks (title, description, priority, project_id, assignee_id, due_date) "
        "VALUES ($1, $2, $3::task_priority, $4, $5, $6) "
        "RETURNING id, title, description, status, priority, project_id, "
        "assignee_id, due_date, created_at, updated_at",
        req.title, req.description, req.priority.value,
        project_id, req.assignee_id, req.due_date,
    )
    logger.info("task created", extra={"task_id": str(result["id"])})
    return TaskOut(**dict(result))


async def update_task(task_id: UUID, req: TaskUpdate, user_id: UUID, db: asyncpg.Connection) -> TaskOut:
    task_row = await db.fetchrow("SELECT id, project_id FROM tasks WHERE id = $1", task_id)
    if not task_row:
        raise HTTPException(status_code=404, detail={"error": "not found"})

    updates = req.model_dump(exclude_none=True)
    if not updates:
        return await _fetch_task(task_id, db)

    # postgres enums need an explicit cast
    enum_casts = {"status": "::task_status", "priority": "::task_priority"}
    set_parts = []
    vals = []
    for i, (field, val) in enumerate(updates.items(), start=2):
        cast = enum_casts.get(field, "")
        set_parts.append(f"{field} = ${i}{cast}")
        vals.append(val.value if hasattr(val, "value") else val)

    set_clause = ", ".join(set_parts)
    updated = await db.fetchrow(
        f"UPDATE tasks SET {set_clause} WHERE id = $1 "
        "RETURNING id, title, description, status, priority, project_id, "
        "assignee_id, due_date, created_at, updated_at",
        task_id, *vals,
    )
    logger.info("task updated", extra={"task_id": str(task_id)})
    return TaskOut(**dict(updated))


async def delete_task(task_id: UUID, user_id: UUID, db: asyncpg.Connection) -> None:
    task_row = await db.fetchrow("SELECT project_id FROM tasks WHERE id = $1", task_id)
    if not task_row:
        raise HTTPException(status_code=404, detail={"error": "not found"})

    # only project owner can delete tasks
    project_row = await db.fetchrow(
        "SELECT owner_id FROM projects WHERE id = $1", task_row["project_id"]
    )
    if project_row["owner_id"] != user_id:
        raise HTTPException(status_code=403, detail={"error": "forbidden"})

    await db.execute("DELETE FROM tasks WHERE id = $1", task_id)
    logger.info("task deleted", extra={"task_id": str(task_id)})


async def _check_project_exists(project_id: UUID, db: asyncpg.Connection) -> None:
    row = await db.fetchrow("SELECT id FROM projects WHERE id = $1", project_id)
    if not row:
        raise HTTPException(status_code=404, detail={"error": "not found"})


async def _check_user_exists(assignee_id: UUID, db: asyncpg.Connection) -> None:
    row = await db.fetchrow("SELECT id FROM users WHERE id = $1", assignee_id)
    if not row:
        raise HTTPException(
            status_code=400,
            detail={"error": "validation failed", "fields": {"assignee_id": "user does not exist"}},
        )


async def _fetch_task(task_id: UUID, db: asyncpg.Connection) -> TaskOut:
    row = await db.fetchrow(
        "SELECT id, title, description, status, priority, project_id, "
        "assignee_id, due_date, created_at, updated_at FROM tasks WHERE id = $1",
        task_id,
    )
    return TaskOut(**dict(row))
    await _assert_project_exists(project_id, db)

    conditions = ["project_id = $1"]
    params: list = [project_id]
    idx = 2

    if status:
        conditions.append(f"status = ${idx}::task_status")
        params.append(status.value)
        idx += 1
    if assignee_id:
        conditions.append(f"assignee_id = ${idx}")
        params.append(assignee_id)
        idx += 1

    offset = (page - 1) * limit
    where = " AND ".join(conditions)
    rows = await db.fetch(
        f"SELECT id, title, description, status, priority, project_id, "
        f"assignee_id, due_date, created_at, updated_at "
        f"FROM tasks WHERE {where} ORDER BY created_at DESC "
        f"LIMIT ${idx} OFFSET ${idx+1}",
        *params, limit, offset,
    )
    return [TaskOut(**dict(r)) for r in rows]


async def create_task(
    project_id: UUID, req: TaskCreate, user_id: UUID, db: asyncpg.Connection
) -> TaskOut:
    await _assert_project_exists(project_id, db)
    if req.assignee_id:
        await _assert_user_exists(req.assignee_id, db)

    row = await db.fetchrow(
        "INSERT INTO tasks (title, description, priority, project_id, assignee_id, due_date) "
        "VALUES ($1, $2, $3::task_priority, $4, $5, $6) "
        "RETURNING id, title, description, status, priority, project_id, "
        "assignee_id, due_date, created_at, updated_at",
        req.title, req.description, req.priority.value,
        project_id, req.assignee_id, req.due_date,
    )
    logger.info("Task created", extra={"task_id": str(row["id"])})
    return TaskOut(**dict(row))


async def update_task(
    task_id: UUID, req: TaskUpdate, user_id: UUID, db: asyncpg.Connection
) -> TaskOut:
    task = await db.fetchrow(
        "SELECT id, project_id FROM tasks WHERE id = $1", task_id
    )
    if not task:
        raise HTTPException(status_code=404, detail={"error": "not found"})

    updates = req.model_dump(exclude_none=True)
    if not updates:
        return await _fetch_task(task_id, db)

    # Cast enum fields to postgres types
    enum_casts = {"status": "::task_status", "priority": "::task_priority"}
    set_parts = []
    values = []
    for i, (k, v) in enumerate(updates.items(), start=2):
        cast = enum_casts.get(k, "")
        set_parts.append(f"{k} = ${i}{cast}")
        values.append(v.value if hasattr(v, "value") else v)

    set_clause = ", ".join(set_parts)
    row = await db.fetchrow(
        f"UPDATE tasks SET {set_clause} WHERE id = $1 "
        "RETURNING id, title, description, status, priority, project_id, "
        "assignee_id, due_date, created_at, updated_at",
        task_id, *values,
    )
    logger.info("Task updated", extra={"task_id": str(task_id)})
    return TaskOut(**dict(row))


async def delete_task(
    task_id: UUID, user_id: UUID, db: asyncpg.Connection
) -> None:
    task = await db.fetchrow(
        "SELECT t.project_id FROM tasks t WHERE t.id = $1", task_id
    )
    if not task:
        raise HTTPException(status_code=404, detail={"error": "not found"})

    project = await db.fetchrow(
        "SELECT owner_id FROM projects WHERE id = $1", task["project_id"]
    )
    if project["owner_id"] != user_id:
        raise HTTPException(status_code=403, detail={"error": "forbidden"})

    await db.execute("DELETE FROM tasks WHERE id = $1", task_id)
    logger.info("Task deleted", extra={"task_id": str(task_id)})


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _assert_project_exists(project_id: UUID, db: asyncpg.Connection) -> None:
    row = await db.fetchrow("SELECT id FROM projects WHERE id = $1", project_id)
    if not row:
        raise HTTPException(status_code=404, detail={"error": "not found"})


async def _assert_user_exists(user_id: UUID, db: asyncpg.Connection) -> None:
    row = await db.fetchrow("SELECT id FROM users WHERE id = $1", user_id)
    if not row:
        raise HTTPException(
            status_code=400,
            detail={"error": "validation failed", "fields": {"assignee_id": "user not found"}},
        )


async def _fetch_task(task_id: UUID, db: asyncpg.Connection) -> TaskOut:
    row = await db.fetchrow(
        "SELECT id, title, description, status, priority, project_id, "
        "assignee_id, due_date, created_at, updated_at FROM tasks WHERE id = $1",
        task_id,
    )
    return TaskOut(**dict(row))
