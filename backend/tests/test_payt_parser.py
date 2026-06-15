"""Testes do parser Payt V1 e normalização de telefone."""

from __future__ import annotations

import pytest

from app.api.routes.inbound_payt import (
    ParseAction,
    normalize_phone,
    parse_payt_postback,
)
from app.models.recoverable_sale import RecoveryFunnelStage, RecoverySaleStatus


# ── Helpers ────────────────────────────────────────────────────────────────────

def _pix_payload(**overrides) -> dict:
    base = {
        "status": "waiting_payment",
        "payment_method": "pix",
        "transaction": {
            "id": "TXN-001",
            "total_price": 19700,
            "pix_url": "https://pay.payt.com.br/pix/TXN-001",
            "pix": {
                "code": "00020126...",
                "expires_at": "2026-06-14T15:00:00+00:00",
            },
        },
        "customer": {"name": "Maria Silva", "phone": "11999998888"},
    }
    base.update(overrides)
    return base


def _abandono_payload(**overrides) -> dict:
    base = {
        "type": "abandoned-cart",
        "status": "pending",
        "transaction": {"id": "CART-001", "total_price": 9900},
        "customer": {"name": "João Costa", "phone": "011999997777"},
        "link": {
            "url": "https://pay.payt.com.br/checkout/CART-001",
            "available_coupons": [{"code": "VOLTA10"}],
        },
    }
    base.update(overrides)
    return base


# ── Cenário 1: Pix pendente enfileira corretamente ────────────────────────────

def test_pix_pendente_enfileira():
    result = parse_payt_postback(_pix_payload())

    assert result.action == ParseAction.ENQUEUE
    assert result.funnel_stage == RecoveryFunnelStage.PIX_PENDENTE
    assert result.external_id == "TXN-001"
    assert result.checkout_url == "https://pay.payt.com.br/pix/TXN-001"
    assert result.expires_at is not None
    assert result.expires_at.year == 2026
    assert result.amount == pytest.approx(197.00)
    assert result.customer_phone == "5511999998888"
    assert result.pix_code == "00020126..."


# ── Cenário 2: Abandono com cupom enfileira corretamente ─────────────────────

def test_abandono_com_cupom_enfileira():
    result = parse_payt_postback(_abandono_payload())

    assert result.action == ParseAction.ENQUEUE
    assert result.funnel_stage == RecoveryFunnelStage.ABANDONO
    assert result.external_id == "CART-001"
    assert result.checkout_url == "https://pay.payt.com.br/checkout/CART-001"
    assert result.coupon == "VOLTA10"
    assert result.customer_phone == "5511999997777"


# ── Cenário 3: status=paid resolve para recovered ─────────────────────────────

def test_paid_resolve_para_recovered():
    payload = {
        "status": "paid",
        "transaction": {"id": "TXN-002", "total_price": 19700},
        "customer": {"name": "Ana", "phone": "11999990001"},
    }
    result = parse_payt_postback(payload)

    assert result.action == ParseAction.RESOLVE
    assert result.new_status == RecoverySaleStatus.RECOVERED
    assert result.external_id == "TXN-002"


# ── Cenário 4: status=expired marca expired ───────────────────────────────────

def test_expired_marca_expired():
    payload = {
        "status": "expired",
        "transaction": {"id": "TXN-003"},
        "customer": {"phone": "11999990002"},
    }
    result = parse_payt_postback(payload)

    assert result.action == ParseAction.RESOLVE
    assert result.new_status == RecoverySaleStatus.EXPIRED


# ── Cenário 5: status=canceled marca lost ─────────────────────────────────────

def test_canceled_marca_lost():
    payload = {
        "status": "canceled",
        "transaction": {"id": "TXN-004"},
        "customer": {"phone": "11999990003"},
    }
    result = parse_payt_postback(payload)

    assert result.action == ParseAction.RESOLVE
    assert result.new_status == RecoverySaleStatus.LOST


# ── Cenário 6: test=true é descartado ────────────────────────────────────────

def test_test_true_descartado():
    payload = _pix_payload()
    payload["test"] = True
    result = parse_payt_postback(payload)

    assert result.action == ParseAction.DISCARD
    assert "test" in result.reason


# ── Cenário 7: phone vazio é descartado ──────────────────────────────────────

def test_phone_vazio_descartado():
    payload = _pix_payload()
    payload["customer"] = {"name": "Ana", "phone": ""}
    result = parse_payt_postback(payload)

    assert result.action == ParseAction.DISCARD
    assert "phone" in result.reason


# ── Cenário 8: cart_recovered=true é descartado ──────────────────────────────

def test_cart_recovered_true_descartado():
    payload = _abandono_payload()
    payload["cart_recovered"] = True
    result = parse_payt_postback(payload)

    assert result.action == ParseAction.DISCARD
    assert "cart_recovered" in result.reason


# ── Cenário 9: paid + cart_recovered → RESOLVE (não descarta) ────────────────

def test_paid_prevalece_sobre_cart_recovered():
    payload = {
        "status": "paid",
        "cart_recovered": True,
        "transaction": {"id": "TXN-005"},
        "customer": {"phone": "11999990004"},
    }
    result = parse_payt_postback(payload)

    # paid tem precedência — deve RESOLVER, não DESCARTAR
    assert result.action == ParseAction.RESOLVE
    assert result.new_status == RecoverySaleStatus.RECOVERED


# ── Cenário 10: normalização de telefone ─────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("011999998888",   "5511999998888"),   # com zero de tronco
    ("11999998888",    "5511999998888"),   # sem zero de tronco
    ("5511999998888",  "5511999998888"),   # já tem DDI
    ("+5511999998888", "5511999998888"),   # com sinal +
    ("(11) 99999-8888", "5511999998888"), # formatado
    ("",               None),             # vazio
    ("abc",            None),             # sem dígitos
])
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


# ── Cenário 11: total_price em centavos → amount correto ─────────────────────

def test_total_price_centavos():
    payload = _pix_payload()
    payload["transaction"]["total_price"] = 19700
    result = parse_payt_postback(payload)

    assert result.amount == pytest.approx(197.00)


# ── Cenário 12: abandono via status=lost_cart (sem type) ─────────────────────

def test_lost_cart_status_enfileira_abandono():
    payload = {
        "status": "lost_cart",
        "transaction": {"id": "CART-002", "total_price": 5000},
        "customer": {"name": "Pedro", "phone": "21988887777"},
        "link": {"url": "https://pay.payt.com.br/checkout/CART-002"},
    }
    result = parse_payt_postback(payload)

    assert result.action == ParseAction.ENQUEUE
    assert result.funnel_stage == RecoveryFunnelStage.ABANDONO
    assert result.amount == pytest.approx(50.00)


# ── Cenário 13: external_id cai para cart_id quando transaction.id ausente ───

def test_external_id_fallback_para_cart_id():
    payload = _abandono_payload()
    # Remove transaction.id, usa cart_id
    payload["transaction"] = {"total_price": 9900}
    payload["cart_id"] = "FALLBACK-CART-999"
    result = parse_payt_postback(payload)

    assert result.action == ParseAction.ENQUEUE
    assert result.external_id == "FALLBACK-CART-999"
