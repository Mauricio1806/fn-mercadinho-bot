"""Testes do validador de delivery."""

import pytest

from app.config import BusinessConfig
from app.core.orders.delivery_validator import (
    extract_block_and_apartment,
    validate_delivery,
)


def make_business(blocos: list[str] = ["A", "B", "C"]) -> BusinessConfig:
    return BusinessConfig(
        {
            "delivery": {
                "tipo": "condominio",
                "blocos": blocos,
                "taxa": 0,
                "pedido_minimo": 0,
            },
            "personalidade": {
                "saudacao": "Olá",
                "despedida": "Tchau",
                "quando_nao_entende": "?",
                "quando_sem_estoque": "sem",
                "quando_fora_area": "fora",
                "girias_baianas": False,
                "tom": "amigável",
            },
            "notificacao": {"whatsapp_dono_1": "TODO", "whatsapp_dono_2": "TODO", "valor_alto": 100},
        }
    )


class TestValidateDelivery:
    def test_bloco_valido(self):
        result = validate_delivery("A", "201", make_business())
        assert result.is_valid is True
        assert result.block == "A"
        assert result.apartment == "201"

    def test_bloco_minusculo_normalizado(self):
        result = validate_delivery("b", "102", make_business())
        assert result.is_valid is True
        assert result.block == "B"

    def test_bloco_com_prefixo_normalizado(self):
        result = validate_delivery("Bloco C", "303", make_business())
        assert result.is_valid is True
        assert result.block == "C"

    def test_bloco_invalido(self):
        result = validate_delivery("Z", "101", make_business())
        assert result.is_valid is False
        assert result.error_message is not None
        assert "Z" in result.error_message

    def test_sem_apartamento(self):
        result = validate_delivery("A", "", make_business())
        assert result.is_valid is False

    def test_sem_blocos_configurados_aceita_qualquer(self):
        business = make_business(blocos=[])
        result = validate_delivery("X", "999", business)
        assert result.is_valid is True

    def test_blocos_todo_ignorados(self):
        """Blocos com valor TODO não devem contar como configurados."""
        business = BusinessConfig(
            {
                "delivery": {"blocos": ["TODO"], "tipo": "condominio", "taxa": 0},
                "personalidade": {
                    "saudacao": "", "despedida": "", "quando_nao_entende": "",
                    "quando_sem_estoque": "", "quando_fora_area": "", "girias_baianas": False, "tom": ""
                },
                "notificacao": {"whatsapp_dono_1": "TODO", "whatsapp_dono_2": "TODO", "valor_alto": 100},
            }
        )
        result = validate_delivery("A", "101", business)
        assert result.is_valid is True  # Sem blocos válidos → aceita qualquer


class TestExtractBlockAndApartment:
    def test_formato_completo(self):
        block, apt = extract_block_and_apartment("Bloco A, apto 201")
        assert block == "A"
        assert apt == "201"

    def test_formato_simples(self):
        block, apt = extract_block_and_apartment("B 302")
        assert block == "B"
        assert apt == "302"

    def test_formato_sem_virgula(self):
        block, apt = extract_block_and_apartment("Bloco C apto 101")
        assert block == "C"
        assert apt == "101"

    def test_sem_informacao(self):
        block, apt = extract_block_and_apartment("não sei o número")
        assert block is None
        assert apt is None

    def test_so_numero(self):
        block, apt = extract_block_and_apartment("201")
        assert block is None
