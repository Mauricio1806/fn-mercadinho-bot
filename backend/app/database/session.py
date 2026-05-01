import os

# Fix Railway DATABASE_URL format (postgres:// → postgresql+asyncpg://)
_db_url = os.getenv("DATABASE_URL", "")
if _db_url.startswith("postgres://"):
    os.environ["DATABASE_URL"] = _db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _db_url.startswith("postgresql://") and "+asyncpg" not in _db_url:
    os.environ["DATABASE_URL"] = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

_engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
    "pool_size": 5,
    "max_overflow": 10,
}

engine = create_async_engine(os.environ.get("DATABASE_URL", settings.database_url), **_engine_kwargs)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
