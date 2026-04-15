"""Testes de autenticação JWT."""

import pytest
from httpx import AsyncClient
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_user import AdminUser

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> AdminUser:
    user = AdminUser(
        email="admin@test.com",
        hashed_password=pwd_context.hash("Senha@Valida123"),
        full_name="Admin",
    )
    db_session.add(user)
    await db_session.flush()
    return user


class TestLogin:
    async def test_login_sucesso(self, client: AsyncClient, admin_user: AdminUser):
        resp = await client.post(
            "/api/auth/login",
            json={"email": "admin@test.com", "password": "Senha@Valida123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_senha_errada(self, client: AsyncClient, admin_user: AdminUser):
        resp = await client.post(
            "/api/auth/login",
            json={"email": "admin@test.com", "password": "senha-errada"},
        )
        assert resp.status_code == 401

    async def test_login_email_inexistente(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/login",
            json={"email": "nao-existe@test.com", "password": "qualquer"},
        )
        assert resp.status_code == 401

    async def test_rota_protegida_sem_token(self, client: AsyncClient):
        resp = await client.get("/api/orders/")
        assert resp.status_code in (401, 403)  # HTTPBearer retorna 403 ou 401 sem token

    async def test_rota_protegida_token_invalido(self, client: AsyncClient):
        resp = await client.get(
            "/api/orders/",
            headers={"Authorization": "Bearer token-invalido"},
        )
        assert resp.status_code == 401


class TestRefreshToken:
    async def test_refresh_valido(self, client: AsyncClient, admin_user: AdminUser):
        login_resp = await client.post(
            "/api/auth/login",
            json={"email": "admin@test.com", "password": "Senha@Valida123"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        resp = await client.post(
            "/api/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_refresh_token_invalido(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/refresh", json={"refresh_token": "token-invalido"}
        )
        assert resp.status_code == 401
