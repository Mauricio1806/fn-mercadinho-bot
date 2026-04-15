"""Testes do módulo de pagamento Pix."""

import pytest

from app.config import BusinessConfig
from app.core.payments.pix import build_pix_message, format_currency


def make_pix_config(configured: bool = True) -> BusinessConfig:
    base: dict = {
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
    if configured:
        base["pix"] = {
            "chave": "123.456.789-00",
            "tipo_chave": "cpf",
            "titular": "Fulano Silva",
            "banco": "Nubank",
        }
    else:
        base["pix"] = {"chave": "TODO"}
    return BusinessConfig(base)


class TestBuildPixMessage:
    def test_mensagem_com_pix_configurado(self):
        config = make_pix_config(configured=True)
        msg = build_pix_message(25.50, config)

        assert "123.456.789-00" in msg
        assert "25,50" in msg or "25.50" in msg
        assert "Fulano Silva" in msg
        assert "Pix" in msg

    def test_mensagem_sem_pix_configurado(self):
        config = make_pix_config(configured=False)
        msg = build_pix_message(25.50, config)

        assert "25,50" in msg or "25.50" in msg
        assert "123.456.789-00" not in msg

    def test_chave_pix_em_code_block(self):
        """A chave Pix deve ser formatada com backtick para facilitar cópia."""
        config = make_pix_config(configured=True)
        msg = build_pix_message(10.00, config)
        assert "`123.456.789-00`" in msg

    def test_valor_zero(self):
        config = make_pix_config(configured=True)
        msg = build_pix_message(0.0, config)
        assert "0,00" in msg or "0.00" in msg


class TestFormatCurrency:
    def test_formata_inteiro(self):
        assert format_currency(10.0) == "R$ 10,00"

    def test_formata_decimal(self):
        assert format_currency(25.50) == "R$ 25,50"

    def test_formata_centavos(self):
        assert format_currency(0.99) == "R$ 0,99"
