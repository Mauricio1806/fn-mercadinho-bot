"""Testes de integração — endpoints exclusivos do superadmin."""

import pytest
from httpx import AsyncClient


class TestSuperadminEndpoints:

    @pytest.mark.asyncio
    async def test_superadmin_cria_tenant(
        self,
        client: AsyncClient,
        superadmin_token: str,
    ):
        resp = await client.post(
            "/api/tenants/",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={
                "slug": "loja-teste-integracao",
                "name": "Loja de Teste Integração",
                "whatsapp_number": "5511888888801",
                "config": {
                    "nome": "Loja de Teste Integração",
                    "pix_chave": "test@email.com",
                    "pix_tipo_chave": "email",
                    "pix_titular": "Loja Teste",
                    "pix_banco": "Nubank",
                    "owners": ["+5511888888801"],
                },
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["slug"] == "loja-teste-integracao"
        assert data["name"] == "Loja de Teste Integração"

    @pytest.mark.asyncio
    async def test_tenant_admin_nao_cria_tenant(
        self,
        client: AsyncClient,
        tenant_fn_token: str,
        tenant_fn,
    ):
        resp = await client.post(
            "/api/tenants/",
            headers={"Authorization": f"Bearer {tenant_fn_token}"},
            json={
                "slug": "tentativa-nao-autorizada",
                "name": "Não Deve Criar",
                "config": {"nome": "x", "pix_chave": "x", "pix_tipo_chave": "cpf",
                           "pix_titular": "x", "pix_banco": "x"},
            },
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_superadmin_lista_todos_tenants(
        self,
        client: AsyncClient,
        superadmin_token: str,
        tenant_fn,
        tenant_padaria,
    ):
        resp = await client.get(
            "/api/tenants/",
            headers={"Authorization": f"Bearer {superadmin_token}"},
        )
        assert resp.status_code == 200
        tenants = resp.json()
        slugs = {t["slug"] for t in tenants}
        assert "fn-mercadinho" in slugs
        assert "padaria-teste" in slugs

    @pytest.mark.asyncio
    async def test_slug_duplicado_retorna_409(
        self,
        client: AsyncClient,
        superadmin_token: str,
        tenant_fn,
    ):
        resp = await client.post(
            "/api/tenants/",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={
                "slug": "fn-mercadinho",
                "name": "Duplicado",
                "config": {"nome": "x", "pix_chave": "x", "pix_tipo_chave": "cpf",
                           "pix_titular": "x", "pix_banco": "x"},
            },
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_patch_tenant_merge_config(
        self,
        client: AsyncClient,
        superadmin_token: str,
        tenant_fn,
    ):
        """PATCH deve fazer merge parcial do config, não substituir tudo."""
        resp = await client.patch(
            f"/api/tenants/{tenant_fn.id}",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={"config": {"nome": "FN Mercadinho Atualizado"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Novo campo presente
        assert data["config"]["nome"] == "FN Mercadinho Atualizado"
        # Campos antigos preservados
        assert "pix_chave" in data["config"]
