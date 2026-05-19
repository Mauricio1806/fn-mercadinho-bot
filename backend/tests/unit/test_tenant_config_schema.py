"""Testes unitários — TenantConfig schema Pydantic."""

import pytest
from pydantic import ValidationError

from app.tenancy.config_schema import TenantConfig


def make_valid_config(**overrides) -> dict:
    base = {
        "nome": "FN Mercadinho",
        "pix_chave": "60747738000149",
        "pix_tipo_chave": "cnpj",
        "pix_titular": "NN Mercadinho",
        "pix_banco": "SumUp",
        "owners": ["+5571991356145"],
    }
    base.update(overrides)
    return base


class TestTenantConfigSchema:

    def test_config_valido_completo(self):
        config = make_valid_config(
            horario={"abertura": "07:00", "fechamento": "21:00"},
            delivery={"taxa_proxima": 3.0, "taxa_distante": 5.0},
            persona={"saudacao": "Olá! 👋"},
            branding={"cor_primaria": "#2E7D32"},
            integracao_estoque={"ativo": False},
        )
        tc = TenantConfig(**config)
        assert tc.nome == "FN Mercadinho"
        assert tc.pix_chave == "60747738000149"
        assert tc.pix_configured is True

    def test_config_minimo_valido(self):
        """Config com apenas nome e pix mínimos deve ser válido."""
        tc = TenantConfig(**make_valid_config())
        assert tc.nome == "FN Mercadinho"
        # Defaults aplicados
        assert tc.horario.abertura == "07:00"
        assert tc.delivery.pedido_minimo == 0.0
        assert tc.persona.usa_emojis is True

    def test_sem_pix_chave_usa_todo(self):
        """Config sem pix_chave usa 'TODO' e pix_configured retorna False."""
        tc = TenantConfig(nome="Sem Pix", pix_chave="TODO",
                          pix_tipo_chave="cnpj", pix_titular="X", pix_banco="Y")
        assert tc.pix_configured is False

    def test_pix_tipo_invalido_lanca_erro(self):
        with pytest.raises(ValidationError) as exc_info:
            TenantConfig(**make_valid_config(pix_tipo_chave="cartao"))
        assert "pix_tipo_chave" in str(exc_info.value)

    def test_integracao_estoque_ativo_sem_sistema_lanca_erro(self):
        """Integração ativa sem sistema definido deve falhar."""
        with pytest.raises(ValidationError) as exc_info:
            TenantConfig(**make_valid_config(
                integracao_estoque={"ativo": True, "sistema": None}
            ))
        assert "sistema" in str(exc_info.value).lower()

    def test_integracao_estoque_ativo_com_sistema_ok(self):
        tc = TenantConfig(**make_valid_config(
            integracao_estoque={"ativo": True, "sistema": "bling", "api_key": "abc123"}
        ))
        assert tc.integracao_estoque.ativo is True
        assert tc.integracao_estoque.sistema == "bling"

    def test_owner_phones_normaliza_mais(self):
        tc = TenantConfig(**make_valid_config(owners=["+5571991356145", "+5511999999999"]))
        phones = tc.owner_phones
        assert "5571991356145" in phones
        assert "5511999999999" in phones
        # Nenhum deve ter '+'
        for p in phones:
            assert not p.startswith("+")

    def test_owners_vazio_ok(self):
        tc = TenantConfig(**make_valid_config(owners=[]))
        assert tc.owner_phones == []

    def test_config_com_campos_extras_ignorados(self):
        """Campos desconhecidos devem ser ignorados (extra='ignore')."""
        config = make_valid_config(campo_inexistente="valor")
        tc = TenantConfig(**config)
        assert tc.nome == "FN Mercadinho"
