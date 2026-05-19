"""Testes unitários — TenantContext."""

import uuid
from unittest.mock import MagicMock

import pytest

from app.tenancy.context import TenantContext
from app.tenancy.config_schema import TenantConfig


def make_mock_tenant(**config_overrides) -> MagicMock:
    base_config = {
        "nome": "FN Mercadinho",
        "pix_chave": "60747738000149",
        "pix_tipo_chave": "cnpj",
        "pix_titular": "NN Mercadinho",
        "pix_banco": "SumUp",
        "horario": {
            "abertura": "07:00",
            "fechamento": "21:00",
            "domingo_abertura": "08:00",
            "domingo_fechamento": "12:30",
        },
        "delivery": {"taxa_proxima": 3.0, "taxa_distante": 5.0, "raio_proxima_metros": 500},
        "owners": ["+5571991356145", "+5571993266224"],
        "comissao_percentual": 5.0,
        "persona": {
            "saudacao": "Olá! Bem-vindo ao FN Mercadinho 👋",
            "despedida": "Obrigado! Até a próxima 😊",
            "girias_regionais": "baianas",
        },
        "branding": {"cor_primaria": "#2E7D32", "cor_secundaria": "#FFA000"},
    }
    base_config.update(config_overrides)

    tenant = MagicMock()
    tenant.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    tenant.slug = "fn-mercadinho"
    tenant.name = "FN Mercadinho"
    tenant.config = base_config
    return tenant


class TestTenantContext:

    def test_from_orm_popula_campos(self):
        tenant = make_mock_tenant()
        ctx = TenantContext.from_orm(tenant)

        assert ctx.nome == "FN Mercadinho"
        assert ctx.slug == "fn-mercadinho"
        assert str(ctx.tenant_id) == "00000000-0000-0000-0000-000000000001"

    def test_pix_chave_retorna_correto(self):
        ctx = TenantContext.from_orm(make_mock_tenant())
        assert ctx.pix_chave == "60747738000149"
        assert ctx.pix_tipo_chave == "cnpj"
        assert ctx.pix_configurado is True if hasattr(ctx, "pix_configurado") else ctx.pix_configured is True

    def test_owner_phones(self):
        ctx = TenantContext.from_orm(make_mock_tenant())
        phones = ctx.owner_phones
        assert len(phones) == 2
        assert "5571991356145" in phones
        assert "5571993266224" in phones

    def test_horario_abertura(self):
        ctx = TenantContext.from_orm(make_mock_tenant())
        assert ctx.horario_abertura == "07:00"
        assert ctx.horario_fechamento == "21:00"
        assert ctx.horario_abertura_domingo == "08:00"

    def test_compat_whatsapp_dono_1(self):
        ctx = TenantContext.from_orm(make_mock_tenant())
        assert ctx.whatsapp_dono_1 == "+5571991356145"
        assert ctx.whatsapp_dono_2 == "+5571993266224"

    def test_girias_baianas_detectado(self):
        ctx = TenantContext.from_orm(make_mock_tenant())
        assert ctx.girias_baianas is True

    def test_campo_opcional_ausente_nao_lanca_excecao(self):
        """Tenant sem campo opcional (ex: instagram) não deve lançar exceção."""
        tenant = make_mock_tenant()
        tenant.config.pop("persona", None)  # Remove persona para usar default
        ctx = TenantContext.from_orm(tenant)
        # Deve usar o default da PersonaConfig
        assert ctx.saudacao is not None

    def test_owners_vazio_retorna_todo(self):
        """Tenant sem owners configurados retorna 'TODO' no compat legado."""
        ctx = TenantContext.from_orm(make_mock_tenant(owners=[]))
        assert ctx.whatsapp_dono_1 == "TODO"
        assert ctx.owner_phones == []

    def test_repr_legivel(self):
        ctx = TenantContext.from_orm(make_mock_tenant())
        r = repr(ctx)
        assert "fn-mercadinho" in r
        assert "FN Mercadinho" in r
