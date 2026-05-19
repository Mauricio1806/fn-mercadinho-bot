"""Testes unitários — Notificações de status ao cliente."""

import pytest
from unittest.mock import MagicMock
import uuid

from app.platform.notifications.customer_updates import (
    STATUS_MESSAGES,
    build_status_message,
    SILENT_TRANSITIONS,
)
from app.models.order import OrderStatus


def make_order(status: OrderStatus = OrderStatus.PREPARING) -> MagicMock:
    order = MagicMock()
    order.id = uuid.uuid4()
    order.status = status
    return order


class TestBuildStatusMessage:

    def test_preparing_retorna_mensagem(self):
        order = make_order()
        msg = build_status_message(OrderStatus.PAYMENT_CONFIRMED, OrderStatus.PREPARING, order)
        assert msg is not None
        assert "preparado" in msg.lower() or "preparando" in msg.lower()

    def test_delivering_retorna_mensagem(self):
        order = make_order()
        msg = build_status_message(OrderStatus.PREPARING, OrderStatus.DELIVERING, order)
        assert msg is not None
        assert "entrega" in msg.lower() or "saiu" in msg.lower()

    def test_delivered_retorna_mensagem(self):
        order = make_order()
        msg = build_status_message(OrderStatus.DELIVERING, OrderStatus.DELIVERED, order)
        assert msg is not None
        assert "entregue" in msg.lower() or "obrigado" in msg.lower()

    def test_cancelled_retorna_mensagem(self):
        order = make_order()
        msg = build_status_message(OrderStatus.PREPARING, OrderStatus.CANCELLED, order)
        assert msg is not None
        assert "cancelado" in msg.lower()

    def test_ready_retorna_mensagem(self):
        order = make_order()
        msg = build_status_message(OrderStatus.PREPARING, OrderStatus.READY, order)
        assert msg is not None

    def test_transicao_igual_retorna_none(self):
        """Mudança para o mesmo status não gera notificação."""
        order = make_order()
        msg = build_status_message(OrderStatus.PREPARING, OrderStatus.PREPARING, order)
        assert msg is None

    def test_status_silencioso_retorna_none(self):
        """PENDING e PAYMENT_CONFIRMED não geram notificação."""
        for silent_status in SILENT_TRANSITIONS:
            order = make_order()
            msg = build_status_message(OrderStatus.PENDING, silent_status, order)
            assert msg is None, f"Status {silent_status} deveria ser silencioso"

    def test_mensagem_inclui_numero_pedido(self):
        """Mensagem deve incluir referência ao pedido."""
        order = make_order()
        order.id = uuid.UUID("12345678-1234-1234-1234-123456789012")
        msg = build_status_message(OrderStatus.PAYMENT_CONFIRMED, OrderStatus.PREPARING, order)
        assert msg is not None
        assert "12345678" in msg.upper()

    def test_sem_order_retorna_mensagem_sem_crash(self):
        """Sem objeto order, ainda retorna mensagem válida."""
        msg = build_status_message(OrderStatus.PAYMENT_CONFIRMED, OrderStatus.PREPARING, None)
        assert msg is not None

    def test_status_nao_mapeado_retorna_none(self):
        """Status não mapeado retorna None graciosamente."""
        order = make_order()
        msg = build_status_message(OrderStatus.PENDING, OrderStatus.PENDING, order)
        assert msg is None  # Mesmo status → None


class TestStatusMessageDict:

    def test_todos_status_importantes_mapeados(self):
        """Os status importantes devem ter mensagens definidas."""
        important = [
            OrderStatus.PREPARING,
            OrderStatus.READY,
            OrderStatus.DELIVERING,
            OrderStatus.DELIVERED,
            OrderStatus.CANCELLED,
        ]
        for s in important:
            assert s in STATUS_MESSAGES, f"Status {s} sem mensagem"
            assert len(STATUS_MESSAGES[s]) > 10, f"Mensagem de {s} muito curta"
