import os

# Corrige URL do Railway ANTES de qualquer import do SQLAlchemy
_url = os.environ.get("DATABASE_URL", "")
if _url.startswith("postgres://"):
    _url = _url.replace("postgres://", "postgresql+asyncpg://", 1)
    os.environ["DATABASE_URL"] = _url
elif _url.startswith("postgresql://") and "+asyncpg" not in _url:
    _url = _url.replace("postgresql://", "postgresql+asyncpg://", 1)
    os.environ["DATABASE_URL"] = _url

if not _url:
    _url = "postgresql+asyncpg://fn_user:changeme@localhost:5432/fn_mercadinho"

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(
    _url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

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
