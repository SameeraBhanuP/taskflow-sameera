from typing import List
from uuid import UUID

from asyncpg import Connection
from fastapi import APIRouter, Depends, Response, status

from app.core.security import get_current_user_id
from app.db.database import get_db
from app.schemas.schemas import (
    ProjectCreate, ProjectDetailOut, ProjectOut, ProjectStatsOut, ProjectUpdate,
)
from app.services import project_service

router = APIRouter()


@router.get("", response_model=List[ProjectOut])
async def list_projects(
    user_id: UUID = Depends(get_current_user_id),
    db: Connection = Depends(get_db),
):
    return await project_service.list_projects(user_id, db)


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    req: ProjectCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: Connection = Depends(get_db),
):
    return await project_service.create_project(req, user_id, db)


@router.get("/{project_id}", response_model=ProjectDetailOut)
async def get_project(
    project_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Connection = Depends(get_db),
):
    return await project_service.get_project(project_id, user_id, db)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: UUID,
    req: ProjectUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: Connection = Depends(get_db),
):
    return await project_service.update_project(project_id, req, user_id, db)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Connection = Depends(get_db),
):
    await project_service.delete_project(project_id, user_id, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/stats", response_model=ProjectStatsOut)
async def project_stats(
    project_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Connection = Depends(get_db),
):
    return await project_service.get_project_stats(project_id, user_id, db)
