"""Fixtures compartilhadas dos testes."""

import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Configura para usar SQLite em memória nos testes
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ENV"] = "test"
os.environ["JWT_SECRET"] = "test-secret-key-for-tests-only"
os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["EVOLUTION_API_KEY"] = "test-evo-key"

from app.config import get_business_config, get_settings  # noqa: E402 (import after env setup)
from app.database.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.base import Base  # noqa: E402

# Engine SQLite para testes
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Cria todas as tabelas antes dos testes e remove ao final."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Sessão de banco com transação pai sempre revertida ao final do teste."""
    async with TestSessionLocal() as session:
        await session.begin_nested()  # Savepoint externo — garante rollback mesmo após commits
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP assíncrono com banco de testes."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        # Commit dentro das rotas vira commit do savepoint interno — não afeta o externo
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, db_session: AsyncSession) -> str:
    """Cria um admin com email único e retorna o JWT de acesso."""
    import uuid as _uuid

    from passlib.context import CryptContext

    from app.models.admin_user import AdminUser

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    unique_email = f"test-{_uuid.uuid4().hex[:8]}@fn-mercadinho.com"
    admin = AdminUser(
        email=unique_email,
        hashed_password=pwd_context.hash("Senha@Test123"),
        full_name="Admin Teste",
    )
    db_session.add(admin)
    await db_session.flush()

    resp = await client.post(
        "/api/auth/login",
        json={"email": unique_email, "password": "Senha@Test123"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]
