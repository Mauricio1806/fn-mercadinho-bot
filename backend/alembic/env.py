"""Alembic migrations environment."""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, create_engine
from sqlalchemy.ext.asyncio import async_engine_from_config, create_async_engine

# Fix URL antes de tudo
def fix_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url

def fix_url_sync(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url

_raw_url = os.environ.get("DATABASE_URL", "")
_async_url = fix_url(_raw_url)
_sync_url = fix_url_sync(_raw_url).replace("+asyncpg", "")

os.environ["DATABASE_URL"] = _async_url

from app.models.base import Base
import app.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    context.configure(
        url=_sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    engine = create_async_engine(_async_url, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()

def run_migrations_online():
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
