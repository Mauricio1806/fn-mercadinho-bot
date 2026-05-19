"""Testes de integração — isolamento de dados entre tenants.

CRÍTICO: garante que tenant A nunca vê dados de tenant B.
"""

import pytest
from httpx import AsyncClient


class TestTenantDataIsolation:
    """Tenant A não pode ver produtos, pedidos nem clientes do Tenant B."""

    @pytest.mark.asyncio
    async def test_produtos_fn_nao_aparecem_para_padaria(
        self,
        client: AsyncClient,
        tenant_fn_token: str,
        tenant_padaria_token: str,
        produtos_fn,
        produtos_padaria,
    ):
        """FN Mercadinho não deve ver produtos da Padaria."""
        # FN vê seus produtos
        resp_fn = await client.get(
            "/api/products/",
            headers={"Authorization": f"Bearer {tenant_fn_token}"},
        )
        assert resp_fn.status_code == 200
        nomes_fn = {p["name"] for p in resp_fn.json()}
        assert all("FN" in nome for nome in nomes_fn)

        # Padaria vê seus produtos
        resp_padaria = await client.get(
            "/api/products/",
            headers={"Authorization": f"Bearer {tenant_padaria_token}"},
        )
        assert resp_padaria.status_code == 200
        nomes_padaria = {p["name"] for p in resp_padaria.json()}
        assert all("Padaria" in nome for nome in nomes_padaria)

        # Nenhum produto do outro tenant deve aparecer
        assert nomes_fn.isdisjoint(nomes_padaria)

    @pytest.mark.asyncio
    async def test_categorias_isoladas_por_tenant(
        self,
        client: AsyncClient,
        tenant_fn_token: str,
        tenant_padaria_token: str,
        produtos_fn,
        produtos_padaria,
    ):
        resp_fn = await client.get(
            "/api/products/categories",
            headers={"Authorization": f"Bearer {tenant_fn_token}"},
        )
        resp_padaria = await client.get(
            "/api/products/categories",
            headers={"Authorization": f"Bearer {tenant_padaria_token}"},
        )

        assert resp_fn.status_code == 200
        assert resp_padaria.status_code == 200

        cats_fn = {c["name"] for c in resp_fn.json()}
        cats_padaria = {c["name"] for c in resp_padaria.json()}

        # Bebidas (FN) e Pães (Padaria) não se misturam
        assert "Bebidas" in cats_fn
        assert "Pães" in cats_padaria
        assert "Pães" not in cats_fn
        assert "Bebidas" not in cats_padaria


class TestSuperadminConsolidado:
    """Superadmin deve ver dados consolidados de todos os tenants."""

    @pytest.mark.asyncio
    async def test_superadmin_ve_stats_consolidados(
        self,
        client: AsyncClient,
        superadmin_token: str,
        tenant_fn,
        tenant_padaria,
    ):
        resp = await client.get(
            "/api/dashboard/consolidated",
            headers={"Authorization": f"Bearer {superadmin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_tenants_active" in data
        assert data["total_tenants_active"] >= 2

    @pytest.mark.asyncio
    async def test_tenant_admin_nao_acessa_consolidated(
        self,
        client: AsyncClient,
        tenant_fn_token: str,
        tenant_fn,
    ):
        resp = await client.get(
            "/api/dashboard/consolidated",
            headers={"Authorization": f"Bearer {tenant_fn_token}"},
        )
        assert resp.status_code == 403
