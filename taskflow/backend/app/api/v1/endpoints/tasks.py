from typing import List, Optional
from uuid import UUID

from asyncpg import Connection
from fastapi import APIRouter, Depends, Query, Response, status

from app.core.security import get_current_user_id
from app.db.database import get_db
from app.schemas.schemas import TaskCreate, TaskOut, TaskStatus, TaskUpdate
from app.services import task_service

router = APIRouter()

# ── Nested under /projects ────────────────────────────────────────────────────

projects_router = APIRouter()


@projects_router.get("/{project_id}/tasks", response_model=List[TaskOut])
async def list_tasks(
    project_id: UUID,
    status: Optional[TaskStatus] = Query(None),
    assignee: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user_id: UUID = Depends(get_current_user_id),
    db: Connection = Depends(get_db),
):
    return await task_service.list_tasks(project_id, user_id, db, status, assignee, page, limit)


@projects_router.post("/{project_id}/tasks", response_model=TaskOut, status_code=201)
async def create_task(
    project_id: UUID,
    req: TaskCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: Connection = Depends(get_db),
):
    return await task_service.create_task(project_id, req, user_id, db)


# ── Top-level /tasks ──────────────────────────────────────────────────────────

@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: UUID,
    req: TaskUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: Connection = Depends(get_db),
):
    return await task_service.update_task(task_id, req, user_id, db)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Connection = Depends(get_db),
):
    await task_service.delete_task(task_id, user_id, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
