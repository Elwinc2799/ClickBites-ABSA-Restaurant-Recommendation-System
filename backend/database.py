import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

_pool: asyncpg.Pool = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=10,
            command_timeout=30,
            ssl='require',
        )
    return _pool


async def reset_pool():
    global _pool
    if _pool:
        try:
            await _pool.close()
        except Exception:
            pass
    _pool = None


async def get_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
