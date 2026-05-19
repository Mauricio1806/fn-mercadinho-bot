"""Testes unitários — isolamento de busca de produtos por tenant."""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestSearchProductsIsolation:
    """Garante que queries de produtos sempre filtram por tenant_id."""

    def test_apply_filter_adiciona_tenant_id(self):
        """TenantScope.apply_filter deve adicionar WHERE tenant_id = :tid."""
        from app.api.middleware.tenant_scope import TenantScope
        from app.models.admin_user import AdminRole
        from sqlalchemy import select
        from app.models.product import Product

        tenant_id = uuid.uuid4()
        user = MagicMock()
        user.role = AdminRole.TENANT_ADMIN
        user.tenant_id = tenant_id

        scope = TenantScope(user=user, tenant_id=tenant_id)
        query = select(Product)
        filtered = scope.apply_filter(query, Product)

        # A query compilada deve conter o tenant_id
        compiled = str(filtered.compile())
        assert "tenant_id" in compiled

    def test_superadmin_nao_adiciona_filtro(self):
        """Superadmin não deve ter filtro de tenant_id."""
        from app.api.middleware.tenant_scope import TenantScope
        from app.models.admin_user import AdminRole
        from sqlalchemy import select
        from app.models.product import Product

        user = MagicMock()
        user.role = AdminRole.SUPERADMIN

        scope = TenantScope(user=user, tenant_id=None)
        query = select(Product)
        filtered = scope.apply_filter(query, Product)

        # Superadmin: query original sem filtro adicional
        assert filtered is query

    def test_assert_owns_tenant_bloqueia_acesso_externo(self):
        """Usuário de tenant A não pode acessar dados de tenant B."""
        from app.api.middleware.tenant_scope import TenantScope
        from app.models.admin_user import AdminRole
        from fastapi import HTTPException

        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()

        user = MagicMock()
        user.role = AdminRole.TENANT_ADMIN
        user.tenant_id = tenant_a

        scope = TenantScope(user=user, tenant_id=tenant_a)

        with pytest.raises(HTTPException) as exc_info:
            scope.assert_owns_tenant(tenant_b)
        assert exc_info.value.status_code == 403

    def test_assert_owns_tenant_permite_acesso_proprio(self):
        """Usuário pode acessar o próprio tenant sem exceção."""
        from app.api.middleware.tenant_scope import TenantScope
        from app.models.admin_user import AdminRole

        tenant_id = uuid.uuid4()
        user = MagicMock()
        user.role = AdminRole.TENANT_ADMIN
        user.tenant_id = tenant_id

        scope = TenantScope(user=user, tenant_id=tenant_id)
        # Não deve lançar exceção
        scope.assert_owns_tenant(tenant_id)

    def test_superadmin_pode_acessar_qualquer_tenant(self):
        """Superadmin pode acessar qualquer tenant sem exceção."""
        from app.api.middleware.tenant_scope import TenantScope
        from app.models.admin_user import AdminRole

        user = MagicMock()
        user.role = AdminRole.SUPERADMIN

        scope = TenantScope(user=user, tenant_id=None)
        # Não deve lançar exceção mesmo com tenant diferente
        scope.assert_owns_tenant(uuid.uuid4())
