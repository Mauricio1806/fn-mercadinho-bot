"""Sessão assíncrona do banco de dados."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()

# SQLite (usado em testes) não suporta pool_size/max_overflow
_is_sqlite = settings.database_url.startswith("sqlite")

_engine_kwargs: dict = {
    "echo": settings.env == "development",
    "pool_pre_ping": not _is_sqlite,
}
if not _is_sqlite:
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_async_engine(settings.database_url, **_engine_kwargs)

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
