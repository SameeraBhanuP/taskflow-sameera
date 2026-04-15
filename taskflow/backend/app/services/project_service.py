import logging
from typing import List
from uuid import UUID

import asyncpg
from fastapi import HTTPException, status

from app.schemas.schemas import (
    ProjectCreate, ProjectDetailOut, ProjectOut, ProjectStatsOut, ProjectUpdate, TaskOut,
)

logger = logging.getLogger(__name__)


async def list_projects(user_id: UUID, db: asyncpg.Connection) -> List[ProjectOut]:
    # get projects where user is owner OR has at least one task assigned
    rows = await db.fetch(
        """
        SELECT DISTINCT p.id, p.name, p.description, p.owner_id, p.created_at
        FROM projects p
        LEFT JOIN tasks t ON t.project_id = p.id
        WHERE p.owner_id = $1 OR t.assignee_id = $1
        ORDER BY p.created_at DESC
        """,
        user_id,
    )
    return [ProjectOut(**dict(r)) for r in rows]


async def create_project(req: ProjectCreate, user_id: UUID, db: asyncpg.Connection) -> ProjectOut:
    result = await db.fetchrow(
        "INSERT INTO projects (name, description, owner_id) VALUES ($1, $2, $3) "
        "RETURNING id, name, description, owner_id, created_at",
        req.name, req.description, user_id,
    )
    logger.info("project created", extra={"project_id": str(result["id"]), "owner": str(user_id)})
    return ProjectOut(**dict(result))


async def get_project(project_id: UUID, user_id: UUID, db: asyncpg.Connection) -> ProjectDetailOut:
    project_row = await db.fetchrow(
        "SELECT id, name, description, owner_id, created_at FROM projects WHERE id = $1",
        project_id,
    )
    if not project_row:
        raise HTTPException(status_code=404, detail={"error": "not found"})

    task_rows = await db.fetch(
        "SELECT id, title, description, status, priority, project_id, "
        "assignee_id, due_date, created_at, updated_at "
        "FROM tasks WHERE project_id = $1 ORDER BY created_at DESC",
        project_id,
    )
    tasks = [TaskOut(**dict(t)) for t in task_rows]
    return ProjectDetailOut(**dict(project_row), tasks=tasks)


async def update_project(
    project_id: UUID, req: ProjectUpdate, user_id: UUID, db: asyncpg.Connection
) -> ProjectOut:
    project_row = await db.fetchrow(
        "SELECT id, owner_id FROM projects WHERE id = $1", project_id
    )
    if not project_row:
        raise HTTPException(status_code=404, detail={"error": "not found"})
    if project_row["owner_id"] != user_id:
        raise HTTPException(status_code=403, detail={"error": "forbidden"})

    updates = req.model_dump(exclude_none=True)
    if not updates:
        return await _fetch_project(project_id, db)

    # build SET clause dynamically based on what was actually sent
    set_clauses = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
    vals = list(updates.values())
    updated = await db.fetchrow(
        f"UPDATE projects SET {set_clauses} WHERE id = $1 "
        "RETURNING id, name, description, owner_id, created_at",
        project_id, *vals,
    )
    return ProjectOut(**dict(updated))


async def delete_project(project_id: UUID, user_id: UUID, db: asyncpg.Connection) -> None:
    project_row = await db.fetchrow(
        "SELECT owner_id FROM projects WHERE id = $1", project_id
    )
    if not project_row:
        raise HTTPException(status_code=404, detail={"error": "not found"})
    if project_row["owner_id"] != user_id:
        raise HTTPException(status_code=403, detail={"error": "forbidden"})

    await db.execute("DELETE FROM projects WHERE id = $1", project_id)
    logger.info("project deleted", extra={"project_id": str(project_id)})


async def get_project_stats(project_id: UUID, user_id: UUID, db: asyncpg.Connection) -> ProjectStatsOut:
    exists = await db.fetchrow("SELECT id FROM projects WHERE id = $1", project_id)
    if not exists:
        raise HTTPException(status_code=404, detail={"error": "not found"})

    status_rows = await db.fetch(
        "SELECT status, COUNT(*) as cnt FROM tasks WHERE project_id = $1 GROUP BY status",
        project_id,
    )
    # group by assignee name, fall back to 'unassigned' if no assignee
    assignee_rows = await db.fetch(
        """
        SELECT COALESCE(u.name, 'unassigned') as label, COUNT(*) as cnt
        FROM tasks t
        LEFT JOIN users u ON u.id = t.assignee_id
        WHERE t.project_id = $1
        GROUP BY label
        """,
        project_id,
    )
    return ProjectStatsOut(
        by_status={r["status"]: r["cnt"] for r in status_rows},
        by_assignee={r["label"]: r["cnt"] for r in assignee_rows},
    )


async def _fetch_project(project_id: UUID, db: asyncpg.Connection) -> ProjectOut:
    row = await db.fetchrow(
        "SELECT id, name, description, owner_id, created_at FROM projects WHERE id = $1",
        project_id,
    )
    return ProjectOut(**dict(row))
