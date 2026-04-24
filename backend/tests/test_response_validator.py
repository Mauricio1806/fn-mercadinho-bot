"""Testes para o checkpoint de qualidade (response_validator)."""

from __future__ import annotations

import pytest

from app.config import BusinessConfig
from app.core.ai.response_validator import validate_response
from app.core.orders.context import OrderContext
from app.models.conversation import ConversationState


# ── Fixtures ──────────────────────────────────────────────────────────────────

_DEFAULT_BLOCOS = ["A", "B", "C"]


def make_business(
    pix_chave: str = "contato@fn-mercadinho.com",
    pix_titular: str = "Fulano da Silva",
    blocos: list[str] | None = None,
    catalogo: list[dict] | None = None,
) -> BusinessConfig:
    raw = {
        "pix": {
            "chave": pix_chave,
            "tipo_chave": "email",
            "titular": pix_titular,
            "banco": "Nubank",
        },
        "delivery": {
            "blocos": _DEFAULT_BLOCOS if blocos is None else blocos,
            "taxa": 3.0,
            "pedido_minimo": 15.0,
        },
        "catalogo": catalogo or [
            {
                "categoria": "Bebidas",
                "produtos": [
                    {"nome": "Agua 500ml", "preco": 2.50},
                    {"nome": "Refrigerante Lata", "preco": 5.00},
                ],
            }
        ],
    }
    return BusinessConfig(raw)


def ctx() -> OrderContext:
    return OrderContext()


# ── Guard de Pix ──────────────────────────────────────────────────────────────

class TestPixGuard:
    def test_pix_key_removed_outside_payment(self):
        business = make_business(pix_chave="contato@fn-mercadinho.com")
        response = "Pague via Pix para contato@fn-mercadinho.com!"

        result = validate_response(response, ConversationState.GREETING, ctx(), business)

        assert "contato@fn-mercadinho.com" not in result.safe_response
        assert "[chave removida]" in result.safe_response
        assert result.was_modified is True
        assert any("SEGURANÇA" in i for i in result.issues)

    def test_pix_key_allowed_in_payment_state(self):
        business = make_business(pix_chave="contato@fn-mercadinho.com")
        response = "Pague R$ 15,00 para a chave contato@fn-mercadinho.com"

        result = validate_response(
            response, ConversationState.ORDER_PAYMENT, ctx(), business
        )

        assert "contato@fn-mercadinho.com" in result.safe_response
        assert result.was_modified is False
        assert result.issues == []

    def test_titular_removed_outside_payment(self):
        business = make_business(pix_titular="Fulano da Silva")
        response = "O titular é Fulano da Silva, manda aí!"

        result = validate_response(response, ConversationState.ORDER_ITEMS, ctx(), business)

        assert "Fulano da Silva" not in result.safe_response
        assert result.was_modified is True

    def test_pix_todo_not_flagged(self):
        """Quando o Pix não está configurado (TODO) não deve disparar alerta."""
        business = make_business(pix_chave="TODO", pix_titular="TODO")
        response = "Pode pagar na entrega!"

        result = validate_response(response, ConversationState.ORDER_CONFIRM, ctx(), business)

        assert result.was_modified is False
        assert result.issues == []

    def test_cnpj_pattern_flagged(self):
        business = make_business()
        response = "CNPJ: 12.345.678/0001-90 — pode transferir!"

        result = validate_response(response, ConversationState.ORDER_ITEMS, ctx(), business)

        assert any("CNPJ" in i for i in result.issues)


# ── Coerência de estado ───────────────────────────────────────────────────────

class TestStateCoherence:
    def test_greeting_with_payment_terms_flagged(self):
        business = make_business()
        response = "Olá! O total do seu pedido é R$ 10,00, pode pagar via Pix!"

        result = validate_response(response, ConversationState.GREETING, ctx(), business)

        assert any("ESTADO" in i for i in result.issues)

    def test_greeting_normal_response_clean(self):
        business = make_business()
        response = "Olá! Bem-vindo ao FN Mercadinho! 😊 Como posso ajudar?"

        result = validate_response(response, ConversationState.GREETING, ctx(), business)

        assert not any("ESTADO" in i for i in result.issues)
        assert result.was_modified is False


# ── Sanity check de preços ────────────────────────────────────────────────────

class TestPriceSanity:
    def test_absurd_price_flagged(self):
        """R$ 9999,00 é muito acima do teto do catálogo (R$ 5,00 × 20 = R$ 100,00)."""
        business = make_business()
        response = "Seu pedido ficou R$ 9999,00."

        result = validate_response(response, ConversationState.ORDER_CONFIRM, ctx(), business)

        assert any("PREÇO" in i for i in result.issues)

    def test_normal_total_clean(self):
        """R$ 25,00 é razoável para um pedido de bebidas."""
        business = make_business()
        response = "Seu pedido: Agua 500ml x2 — R$ 5,00. Total: R$ 5,00."

        result = validate_response(response, ConversationState.ORDER_CONFIRM, ctx(), business)

        price_issues = [i for i in result.issues if "PREÇO" in i]
        assert price_issues == []

    def test_price_outside_order_state_not_checked(self):
        """Verificação de preço só acontece em estados de pedido."""
        business = make_business()
        response = "Nosso refrigerante custa R$ 5,00."

        result = validate_response(response, ConversationState.MAIN_MENU, ctx(), business)

        assert not any("PREÇO" in i for i in result.issues)


# ── Blocos de entrega ─────────────────────────────────────────────────────────

class TestDeliveryBlocks:
    def test_invalid_block_flagged(self):
        """Claude mencionando bloco Z (fora da área) deve ser auditado."""
        business = make_business(blocos=["A", "B", "C"])
        response = "Perfeito! Vou entregar no bloco Z, apartamento 301."

        result = validate_response(
            response, ConversationState.ORDER_DELIVERY, ctx(), business
        )

        assert any("ENTREGA" in i for i in result.issues)
        # Texto NÃO é modificado — apenas auditado
        assert result.was_modified is False

    def test_valid_block_clean(self):
        business = make_business(blocos=["A", "B", "C"])
        response = "Certo! Entrego no bloco A, apartamento 101. 🛵"

        result = validate_response(
            response, ConversationState.ORDER_DELIVERY, ctx(), business
        )

        assert not any("ENTREGA" in i for i in result.issues)

    def test_no_blocks_configured_skips_check(self):
        """Sem blocos configurados, qualquer menção passa livre."""
        business = make_business(blocos=[])
        response = "Entrego no bloco Z!"

        result = validate_response(
            response, ConversationState.ORDER_DELIVERY, ctx(), business
        )

        assert not any("ENTREGA" in i for i in result.issues)

    def test_block_check_only_in_delivery_states(self):
        """Blocos mencionados em outros estados não disparam alerta."""
        business = make_business(blocos=["A", "B"])
        response = "Ótimo! No bloco Z?"

        result = validate_response(response, ConversationState.GREETING, ctx(), business)

        assert not any("ENTREGA" in i for i in result.issues)


# ── Caso sem problemas ────────────────────────────────────────────────────────

class TestCleanResponse:
    def test_normal_order_response_passes_all_checks(self):
        business = make_business()
        response = (
            "Seu pedido:\n"
            "• Agua 500ml x2 — R$ 5,00\n"
            "• Refrigerante Lata x1 — R$ 5,00\n"
            "Total: R$ 10,00\n"
            "Confirma? 😊"
        )

        result = validate_response(
            response, ConversationState.ORDER_CONFIRM, ctx(), business
        )

        assert result.issues == []
        assert result.was_modified is False
        assert result.safe_response == response
