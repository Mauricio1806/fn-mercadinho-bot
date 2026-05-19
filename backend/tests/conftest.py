"""Fixtures compartilhadas dos testes — multi-tenant."""

import asyncio
import os
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Configura para usar SQLite em memória nos testes
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ENV"] = "test"
os.environ["JWT_SECRET"] = "test-secret-key-for-tests-only-multitenant"
os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["EVOLUTION_API_KEY"] = "test-evo-key"

from app.config import get_settings  # noqa: E402
from app.database.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models.admin_user import AdminRole, AdminUser  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402
from app.models.product import Product, ProductCategory  # noqa: E402

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# UUIDs fixos para testes
FN_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")
PADARIA_UUID = uuid.UUID("00000000-0000-0000-0000-000000000002")
FARMACIA_UUID = uuid.UUID("00000000-0000-0000-0000-000000000003")

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


def _make_tenant_config(nome: str, pix_chave: str = "00000000000") -> dict:
    return {
        "nome": nome,
        "pix_chave": pix_chave,
        "pix_tipo_chave": "cpf",
        "pix_titular": nome,
        "pix_banco": "Nubank",
        "horario": {"abertura": "08:00", "fechamento": "18:00",
                    "msg_fora_horario": "Fechado!"},
        "delivery": {"taxa_proxima": 5.0, "taxa_distante": 8.0},
        "owners": ["+5511999999001"],
        "comissao_percentual": 5.0,
        "persona": {"saudacao": f"Olá! Bem-vindo à {nome}!", "despedida": "Obrigado!"},
        "branding": {"cor_primaria": "#1976D2"},
        "integracao_estoque": {"ativo": False},
    }


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Cria todas as tabelas antes dos testes e remove ao final."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """Sessão de banco com rollback garantido ao final do teste."""
    async with TestSessionLocal() as session:
        await session.begin_nested()
        yield session
        await session.rollback()


# Alias compat com testes legados
@pytest_asyncio.fixture
async def db_session(async_session: AsyncSession) -> AsyncSession:
    return async_session


@pytest_asyncio.fixture
async def tenant_fn(async_session: AsyncSession) -> Tenant:
    tenant = Tenant(
        id=FN_UUID,
        slug="fn-mercadinho",
        name="FN Mercadinho",
        whatsapp_number="557199371599",
        is_active=True,
        config=_make_tenant_config("FN Mercadinho", "60747738000149"),
    )
    async_session.add(tenant)
    await async_session.flush()
    return tenant


@pytest_asyncio.fixture
async def tenant_padaria(async_session: AsyncSession) -> Tenant:
    tenant = Tenant(
        id=PADARIA_UUID,
        slug="padaria-teste",
        name="Padaria Teste",
        whatsapp_number="5511999999001",
        is_active=True,
        config=_make_tenant_config("Padaria Teste"),
    )
    async_session.add(tenant)
    await async_session.flush()
    return tenant


@pytest_asyncio.fixture
async def tenant_farmacia(async_session: AsyncSession) -> Tenant:
    tenant = Tenant(
        id=FARMACIA_UUID,
        slug="farmacia-teste",
        name="Farmácia Teste",
        whatsapp_number="5521999999002",
        is_active=True,
        config=_make_tenant_config("Farmácia Teste"),
    )
    async_session.add(tenant)
    await async_session.flush()
    return tenant


async def _create_admin(session, email: str, role: AdminRole, tenant_id=None) -> AdminUser:
    admin = AdminUser(
        email=email,
        hashed_password=pwd_context.hash("Senha@Test123"),
        full_name=f"Admin {role.value}",
        role=role,
        tenant_id=tenant_id,
        is_active=True,
    )
    session.add(admin)
    await session.flush()
    return admin


async def _get_token(client, email: str) -> str:
    resp = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "Senha@Test123"},
    )
    assert resp.status_code == 200, f"Login falhou para {email}: {resp.text}"
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def client(async_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def superadmin_token(
    client: AsyncClient, async_session: AsyncSession
) -> str:
    await _create_admin(async_session, "superadmin@test.com", AdminRole.SUPERADMIN)
    return await _get_token(client, "superadmin@test.com")


@pytest_asyncio.fixture
async def tenant_fn_token(
    client: AsyncClient,
    async_session: AsyncSession,
    tenant_fn: Tenant,
) -> str:
    await _create_admin(async_session, "admin-fn@test.com", AdminRole.TENANT_ADMIN, FN_UUID)
    return await _get_token(client, "admin-fn@test.com")


@pytest_asyncio.fixture
async def tenant_padaria_token(
    client: AsyncClient,
    async_session: AsyncSession,
    tenant_padaria: Tenant,
) -> str:
    await _create_admin(async_session, "admin-padaria@test.com", AdminRole.TENANT_ADMIN, PADARIA_UUID)
    return await _get_token(client, "admin-padaria@test.com")


@pytest_asyncio.fixture
async def produtos_fn(async_session: AsyncSession, tenant_fn: Tenant) -> list[Product]:
    cat = ProductCategory(tenant_id=FN_UUID, name="Bebidas", sort_order=0, is_active=True)
    async_session.add(cat)
    await async_session.flush()

    produtos = [
        Product(tenant_id=FN_UUID, name=f"Produto FN {i}", price=float(i * 5),
                category_id=cat.id, is_available=True)
        for i in range(1, 4)
    ]
    for p in produtos:
        async_session.add(p)
    await async_session.flush()
    return produtos


@pytest_asyncio.fixture
async def produtos_padaria(async_session: AsyncSession, tenant_padaria: Tenant) -> list[Product]:
    cat = ProductCategory(tenant_id=PADARIA_UUID, name="Pães", sort_order=0, is_active=True)
    async_session.add(cat)
    await async_session.flush()

    produtos = [
        Product(tenant_id=PADARIA_UUID, name=f"Produto Padaria {i}", price=float(i * 3),
                category_id=cat.id, is_available=True)
        for i in range(1, 3)
    ]
    for p in produtos:
        async_session.add(p)
    await async_session.flush()
    return produtos


# Token admin legado (compat com testes existentes)
@pytest_asyncio.fixture
async def admin_token(
    client: AsyncClient, async_session: AsyncSession, tenant_fn: Tenant
) -> str:
    return await (tenant_fn_token.__wrapped__(client, async_session, tenant_fn)
                  if hasattr(tenant_fn_token, "__wrapped__") else
                  _get_admin_token_compat(client, async_session))


async def _get_admin_token_compat(client, session):
    import uuid as _uuid
    email = f"test-{_uuid.uuid4().hex[:8]}@fn-mercadinho.com"
    await _create_admin(session, email, AdminRole.TENANT_ADMIN, FN_UUID)
    return await _get_token(client, email)
