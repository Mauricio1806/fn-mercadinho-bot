"""Testes unitários — TenantResolver."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.tenancy.resolver import normalize_phone, resolve_tenant_by_number, invalidate_cache


class TestNormalizePhone:

    def test_remove_mais(self):
        assert normalize_phone("+5571991356145") == "5571991356145"

    def test_remove_espacos(self):
        assert normalize_phone("+55 71 99135-6145") == "5571991356145"

    def test_remove_hifen(self):
        assert normalize_phone("71 99135-6145") == "7199135-6145".replace("-", "")

    def test_numero_sem_plus_inalterado(self):
        assert normalize_phone("5571991356145") == "5571991356145"

    def test_formatos_equivalentes(self):
        """Formatos diferentes do mesmo número devem normalizar para o mesmo valor."""
        n1 = normalize_phone("+5571991356145")
        n2 = normalize_phone("5571991356145")
        n3 = normalize_phone("+55 71 99135-6145")
        assert n1 == n2 == n3


class TestResolveTenantByNumber:

    @pytest.mark.asyncio
    async def test_resolve_fn_mercadinho(self):
        """Mock do banco: número do FN Mercadinho retorna o tenant correto."""
        from app.tenancy.context import TenantContext

        mock_tenant = MagicMock()
        mock_tenant.id = "00000000-0000-0000-0000-000000000001"
        mock_tenant.slug = "fn-mercadinho"
        mock_tenant.name = "FN Mercadinho"
        mock_tenant.config = {
            "nome": "FN Mercadinho",
            "pix_chave": "60747738000149",
            "pix_tipo_chave": "cnpj",
            "pix_titular": "NN Mercadinho",
            "pix_banco": "SumUp",
        }

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Limpa cache antes do teste
        invalidate_cache()

        ctx = await resolve_tenant_by_number("5571999371599", mock_db)
        assert ctx is not None
        assert ctx.slug == "fn-mercadinho"
        assert ctx.nome == "FN Mercadinho"

    @pytest.mark.asyncio
    async def test_numero_inexistente_retorna_none(self):
        """Número não cadastrado retorna None."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        invalidate_cache()
        ctx = await resolve_tenant_by_number("9999999999999", mock_db)
        assert ctx is None

    @pytest.mark.asyncio
    async def test_cache_evita_query_repetida(self):
        """Segunda chamada com mesmo número deve usar cache, não DB."""
        from app.tenancy.context import TenantContext

        mock_tenant = MagicMock()
        mock_tenant.id = "00000000-0000-0000-0000-000000000001"
        mock_tenant.slug = "fn-mercadinho"
        mock_tenant.name = "FN Mercadinho"
        mock_tenant.config = {
            "nome": "FN Mercadinho", "pix_chave": "x",
            "pix_tipo_chave": "cnpj", "pix_titular": "x", "pix_banco": "x",
        }

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute = AsyncMock(return_value=mock_result)

        invalidate_cache()
        await resolve_tenant_by_number("5571999371599", mock_db)
        await resolve_tenant_by_number("5571999371599", mock_db)

        # DB deve ter sido chamado apenas 1 vez (segunda foi do cache)
        assert mock_db.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_normalizacao_resolve_mesmo_tenant(self):
        """Formatos diferentes do mesmo número resolvem o mesmo tenant."""
        mock_tenant = MagicMock()
        mock_tenant.id = "00000000-0000-0000-0000-000000000001"
        mock_tenant.slug = "fn-mercadinho"
        mock_tenant.name = "FN Mercadinho"
        mock_tenant.config = {
            "nome": "FN Mercadinho", "pix_chave": "x",
            "pix_tipo_chave": "cnpj", "pix_titular": "x", "pix_banco": "x",
        }

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute = AsyncMock(return_value=mock_result)

        invalidate_cache()
        ctx1 = await resolve_tenant_by_number("+5571999371599", mock_db)
        invalidate_cache()
        ctx2 = await resolve_tenant_by_number("5571999371599", mock_db)

        assert ctx1 is not None
        assert ctx2 is not None
        assert ctx1.slug == ctx2.slug
