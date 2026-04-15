import logging
import signal
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.endpoints import auth, projects, tasks
from app.api.v1.endpoints.tasks import projects_router as tasks_under_projects
from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.database import create_pool
    logger.info("TaskFlow API starting up", extra={"env": settings.ENVIRONMENT})
    app.state.pool = await create_pool(settings.DATABASE_URL)
    yield
    await app.state.pool.close()
    logger.info("TaskFlow API shutting down")


app = FastAPI(
    title="TaskFlow API",
    description="Task management system — Zomato take-home",
    version="1.0.0",
    lifespan=lifespan,
)

# exception handlers — errors must match spec format: {"error": ..., "fields": ...}

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    If the service already raised with a dict detail (e.g. {"error": "not found"}),
    pass it through unchanged. Otherwise wrap the string detail.
    """
    if isinstance(exc.detail, dict):
        body = exc.detail
    else:
        body = {"error": exc.detail}
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Convert Pydantic v2 validation errors into the spec's structured format."""
    fields = {}
    for err in exc.errors():
        loc = err.get("loc", [])
        field = str(loc[-1]) if loc else "unknown"
        fields[field] = err.get("msg", "invalid")
    return JSONResponse(
        status_code=422,
        content={"error": "validation failed", "fields": fields},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(tasks_under_projects, prefix="/projects", tags=["tasks"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])


@app.get("/health")
async def health():
    return {"status": "ok"}


def handle_sigterm(*_):
    logger.info("Received SIGTERM, shutting down gracefully")
    sys.exit(0)


signal.signal(signal.SIGTERM, handle_sigterm)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
