from typing import AsyncGenerator

import asyncpg
from fastapi import Request


async def get_db(request: Request) -> AsyncGenerator[asyncpg.Connection, None]:
    """Yield a connection from the pool stored in app state."""
    async with request.app.state.pool.acquire() as conn:
        yield conn


async def create_pool(dsn: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10)
