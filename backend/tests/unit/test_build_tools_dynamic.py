"""Testes unitários — build_tools dinâmico por tenant."""

import pytest


class TestBuildToolsDynamic:
    """
    Garante que o prompt builder usa o nome do tenant dinâmico,
    nunca retorna 'FN Mercadinho' hardcoded para outros tenants.
    """

    def _make_context(self, nome: str):
        from unittest.mock import MagicMock
        import uuid

        mock_tenant = MagicMock()
        mock_tenant.id = uuid.uuid4()
        mock_tenant.slug = nome.lower().replace(" ", "-")
        mock_tenant.name = nome
        mock_tenant.config = {
            "nome": nome,
            "pix_chave": "00000000000",
            "pix_tipo_chave": "cpf",
            "pix_titular": nome,
            "pix_banco": "Nubank",
            "horario": {"abertura": "08:00", "fechamento": "18:00"},
            "persona": {"saudacao": f"Olá! Bem-vindo à {nome} 👋"},
        }

        from app.tenancy.context import TenantContext
        return TenantContext.from_orm(mock_tenant)

    def test_prompt_padaria_tem_nome_padaria(self):
        """Prompt para Padaria São João deve conter o nome correto."""
        from app.core.ai.prompt_builder import build_system_prompt
        from app.models.conversation import ConversationState

        ctx = self._make_context("Padaria São João")
        prompt = build_system_prompt(ConversationState.GREETING, business=ctx)

        assert "Padaria São João" in prompt
        assert "FN Mercadinho" not in prompt

    def test_prompt_farmacia_tem_nome_farmacia(self):
        """Prompt para Farmácia Central deve conter o nome correto."""
        from app.core.ai.prompt_builder import build_system_prompt
        from app.models.conversation import ConversationState

        ctx = self._make_context("Farmácia Central")
        prompt = build_system_prompt(ConversationState.GREETING, business=ctx)

        assert "Farmácia Central" in prompt
        assert "FN Mercadinho" not in prompt

    def test_prompt_fn_mercadinho_tem_fn_no_nome(self):
        """Prompt para FN Mercadinho deve conter o nome correto."""
        from app.core.ai.prompt_builder import build_system_prompt
        from app.models.conversation import ConversationState

        ctx = self._make_context("FN Mercadinho")
        prompt = build_system_prompt(ConversationState.GREETING, business=ctx)

        assert "FN Mercadinho" in prompt

    def test_saudacao_usa_nome_do_tenant(self):
        """A saudação no contexto deve vir do tenant, não hardcoded."""
        ctx = self._make_context("Mercearia da Vila")
        assert "Mercearia da Vila" in ctx.saudacao
