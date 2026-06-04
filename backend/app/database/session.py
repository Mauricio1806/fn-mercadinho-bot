"""Sessão assíncrona do banco de dados."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()

# Normaliza URL: Railway/Heroku entregam postgresql:// mas precisamos do driver asyncpg
def _normalize_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url

_db_url = _normalize_db_url(settings.database_url)

# SQLite (usado em testes) não suporta pool_size/max_overflow
_is_sqlite = _db_url.startswith("sqlite")

_engine_kwargs: dict = {
    "echo": settings.env == "development",
    "pool_pre_ping": not _is_sqlite,
}
if not _is_sqlite:
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_async_engine(_db_url, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency do FastAPI: fornece uma sessão de banco por request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
