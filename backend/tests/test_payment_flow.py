"""Testes do fluxo completo de pagamento: ORDER_PAYMENT → PAYMENT_RECEIPT → CLOSED."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import BusinessConfig
from app.core.conversation.engine import ConversationEngine
from app.core.whatsapp.types import InboundMessage, WhatsAppMessageType
from app.models.conversation import Conversation, ConversationState
from app.models.customer import Customer
from app.models.order import Order, OrderStatus


def make_business() -> BusinessConfig:
    return BusinessConfig(
        {
            "mercadinho": {"nome": "FN Test"},
            "horario": {"abertura": "00:00", "fechamento": "23:59", "dias": "Todos"},
            "delivery": {"tipo": "condominio", "blocos": ["A", "B"]},
            "pix": {"chave": "test@pix.com", "tipo_chave": "email", "titular": "Teste"},
            "personalidade": {
                "saudacao": "Olá!",
                "despedida": "Tchau!",
                "quando_nao_entende": "Hm?",
                "quando_sem_estoque": "Sem estoque.",
                "quando_fora_area": "Fora da área.",
                "girias_baianas": False,
                "tom": "amigável",
            },
            "notificacao": {
                "whatsapp_dono_1": "TODO",
                "whatsapp_dono_2": "TODO",
                "valor_alto": 100,
                "comissao_percentual": 5.0,
            },
        }
    )


def make_inbound(
    phone: str = "5571999990099",
    text: str = "oi",
    msg_type: WhatsAppMessageType = WhatsAppMessageType.TEXT,
    image_url: str | None = None,
) -> InboundMessage:
    return InboundMessage(
        phone=phone,
        name="Cliente Teste",
        text=text,
        message_id=f"MSG-{uuid.uuid4().hex[:8]}",
        message_type=msg_type,
        timestamp=1700000000,
        image_url=image_url,
    )


class TestPaymentReceiptState:
    """Testa que ORDER_PAYMENT avança para PAYMENT_RECEIPT após bot enviar PIX."""

    def test_state_machine_order_payment_para_payment_receipt(self):
        from app.core.conversation.handlers import next_state_from_response
        from app.models.conversation import ConversationState

        state = next_state_from_response(
            ConversationState.ORDER_PAYMENT,
            "Ótimo! Pague via Pix: `test@pix.com`\nApós pagar, envie o comprovante 📎",
            "ok",
        )
        assert state == ConversationState.PAYMENT_RECEIPT

    def test_state_machine_payment_receipt_mantém_estado_com_texto(self):
        from app.core.conversation.handlers import next_state_from_response
        from app.models.conversation import ConversationState

        state = next_state_from_response(
            ConversationState.PAYMENT_RECEIPT,
            "Ainda aguardando o comprovante 😊",
            "já vou mandar",
        )
        assert state == ConversationState.PAYMENT_RECEIPT

    def test_transicao_payment_receipt_para_closed_valida(self):
        from app.core.conversation.states import is_valid_transition

        assert is_valid_transition(
            ConversationState.PAYMENT_RECEIPT, ConversationState.CLOSED
        )

    def test_transicao_order_payment_para_payment_receipt_valida(self):
        from app.core.conversation.states import is_valid_transition

        assert is_valid_transition(
            ConversationState.ORDER_PAYMENT, ConversationState.PAYMENT_RECEIPT
        )


class TestReceiptEngineIntegration:
    """Testa o engine quando recebe imagem/PDF em estado de pagamento."""

    @pytest.fixture
    def mock_claude(self):
        claude = AsyncMock()
        claude.chat = AsyncMock(return_value=("Envie o comprovante PIX 📎", 100))
        claude.chat_with_image = AsyncMock(return_value=(
            json.dumps({
                "status": "concluido",
                "amount": 50.0,
                "recipient_name": "fn mercadinho",
                "recipient_key": "test@pix.com",
                "payer_name": "Cliente Teste",
                "txid": None,
                "date": None,
                "time": None,
                "bank": "Nubank",
                "is_screenshot": False,
                "confidence": "high",
                "raw_text": "Pix concluido de R$ 50,00 para fn mercadinho",
            }),
            200,
        ))
        return claude

    @pytest.fixture
    def mock_whatsapp(self):
        wa = AsyncMock()
        wa.send_text = AsyncMock(return_value=True)
        wa.send_typing = AsyncMock()
        wa.send_audio_url = AsyncMock(return_value=True)
        wa.send_image_url = AsyncMock(return_value=True)
        return wa

    async def test_imagem_em_payment_receipt_valida_e_fecha(
        self,
        db_session: AsyncSession,
        mock_claude,
        mock_whatsapp,
    ):
        business = make_business()

        # Cria customer + conversa no estado PAYMENT_RECEIPT com pedido pendente
        customer = Customer(phone="5571999990088", name="Cliente Pix")
        db_session.add(customer)
        await db_session.flush()

        order = Order(
            customer_id=customer.id,
            total_amount=50.00,
            status=OrderStatus.PENDING,
        )
        db_session.add(order)
        await db_session.flush()

        ctx_json = json.dumps({"items": [], "delivery_type": "delivery", "building_block": "A", "apartment": "201", "total": 50.0, "order_id": str(order.id), "notes": None})
        conv = Conversation(
            customer_id=customer.id,
            state=ConversationState.PAYMENT_RECEIPT,
            status="active",
            context_json=ctx_json,
        )
        db_session.add(conv)
        await db_session.flush()

        engine = ConversationEngine(
            db=db_session,
            claude=mock_claude,
            whatsapp=mock_whatsapp,
            business=business,
        )

        with patch(
            "app.core.payments.receipt_validator._download",
            return_value=("base64data", "image/jpeg"),
        ):
            msg = make_inbound(
                phone="5571999990088",
                text="",
                msg_type=WhatsAppMessageType.IMAGE,
                image_url="http://fake/comprovante.jpg",
            )
            await engine.handle(msg)

        # Atualiza a sessão para ver as mudanças
        await db_session.refresh(order)
        assert order.status == OrderStatus.PAYMENT_CONFIRMED
        assert order.pix_confirmed is True

    async def test_texto_em_payment_receipt_mantém_estado(
        self,
        db_session: AsyncSession,
        mock_claude,
        mock_whatsapp,
    ):
        business = make_business()

        customer = Customer(phone="5571999990077", name="Aguardando")
        db_session.add(customer)
        await db_session.flush()

        order = Order(
            customer_id=customer.id,
            total_amount=30.00,
            status=OrderStatus.PENDING,
        )
        db_session.add(order)
        await db_session.flush()

        ctx_json = json.dumps({"items": [], "delivery_type": "delivery", "building_block": None, "apartment": None, "total": 30.0, "order_id": str(order.id), "notes": None})
        conv = Conversation(
            customer_id=customer.id,
            state=ConversationState.PAYMENT_RECEIPT,
            status="active",
            context_json=ctx_json,
        )
        db_session.add(conv)
        await db_session.flush()

        engine = ConversationEngine(
            db=db_session,
            claude=mock_claude,
            whatsapp=mock_whatsapp,
            business=business,
        )

        msg = make_inbound(phone="5571999990077", text="já vou mandar o comprovante")
        await engine.handle(msg)

        await db_session.refresh(conv)
        assert conv.state == ConversationState.PAYMENT_RECEIPT
        # Pedido ainda pendente
        await db_session.refresh(order)
        assert order.status == OrderStatus.PENDING
