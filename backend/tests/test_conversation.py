"""Testes da máquina de estados e engine de conversa."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import BusinessConfig
from app.core.conversation.engine import ConversationEngine
from app.core.conversation.handlers import (
    extract_order_total,
    next_state_from_response,
    trim_history,
)
from app.core.conversation.states import classify_intent, is_valid_transition
from app.core.whatsapp.types import InboundMessage, WhatsAppMessageType
from app.models.conversation import ConversationState
from app.models.customer import Customer


# ── Testes de máquina de estados ────────────────────────────────────────────

class TestStateTransitions:
    def test_greeting_para_main_menu(self):
        assert is_valid_transition(ConversationState.GREETING, ConversationState.MAIN_MENU)

    def test_main_menu_para_order_items(self):
        assert is_valid_transition(ConversationState.MAIN_MENU, ConversationState.ORDER_ITEMS)

    def test_order_items_para_order_confirm(self):
        assert is_valid_transition(ConversationState.ORDER_ITEMS, ConversationState.ORDER_CONFIRM)

    def test_order_payment_para_payment_receipt(self):
        assert is_valid_transition(ConversationState.ORDER_PAYMENT, ConversationState.PAYMENT_RECEIPT)

    def test_payment_receipt_para_closed(self):
        assert is_valid_transition(ConversationState.PAYMENT_RECEIPT, ConversationState.CLOSED)

    def test_closed_permite_reinicio(self):
        assert is_valid_transition(ConversationState.CLOSED, ConversationState.GREETING)

    def test_transicao_invalida(self):
        assert not is_valid_transition(ConversationState.GREETING, ConversationState.ORDER_PAYMENT)

    def test_transicao_invalida_pula_estados(self):
        assert not is_valid_transition(ConversationState.GREETING, ConversationState.CLOSED)


class TestClassifyIntent:
    def test_detecta_pedido(self):
        assert classify_intent("quero fazer um pedido") == "order"
        assert classify_intent("1") == "order"

    def test_detecta_delivery(self):
        assert classify_intent("como funciona a entrega?") == "delivery"
        assert classify_intent("2") == "delivery"

    def test_detecta_horario(self):
        assert classify_intent("que horas abre?") == "hours"
        assert classify_intent("3") == "hours"

    def test_detecta_confirmacao(self):
        assert classify_intent("sim, confirmo") == "confirm"
        assert classify_intent("ok") == "confirm"

    def test_detecta_cancelamento(self):
        assert classify_intent("não quero mais") == "cancel"
        assert classify_intent("cancela") == "cancel"

    def test_outro(self):
        assert classify_intent("bom dia!") == "other"


class TestNextState:
    def test_greeting_sempre_vai_para_main_menu(self):
        state = next_state_from_response(
            ConversationState.GREETING, "Olá! Bem-vindo 👋 O que posso fazer?", "oi"
        )
        assert state == ConversationState.MAIN_MENU

    def test_order_items_vai_para_confirm_quando_total(self):
        state = next_state_from_response(
            ConversationState.ORDER_ITEMS,
            "📦 Seu pedido:\n• Coca-Cola x1\n💰 Total: R$ 10,00\nDeseja confirmar?",
            "isso mesmo",
        )
        assert state == ConversationState.ORDER_CONFIRM

    def test_order_items_cancela_volta_ao_menu(self):
        state = next_state_from_response(
            ConversationState.ORDER_ITEMS,
            "Tudo bem, pedido cancelado!",
            "cancela o pedido",
        )
        assert state == ConversationState.MAIN_MENU

    def test_order_delivery_avanca_para_payment(self):
        state = next_state_from_response(
            ConversationState.ORDER_DELIVERY,
            "Ótimo! 💰 Pagar via Pix\nChave: 123\nValor: R$ 15,00",
            "Bloco A, apto 201",
        )
        assert state == ConversationState.ORDER_PAYMENT

    def test_payment_aguarda_comprovante(self):
        state = next_state_from_response(
            ConversationState.ORDER_PAYMENT, "Ótimo! Agora envie o comprovante PIX 📎", "ok"
        )
        assert state == ConversationState.PAYMENT_RECEIPT

    def test_payment_receipt_mantém_estado(self):
        state = next_state_from_response(
            ConversationState.PAYMENT_RECEIPT, "Ainda aguardando o comprovante 😊", "já vou mandar"
        )
        assert state == ConversationState.PAYMENT_RECEIPT

    def test_closed_reinicia_com_greeting(self):
        state = next_state_from_response(
            ConversationState.CLOSED, "Olá! Bem-vindo!", "oi de novo"
        )
        assert state == ConversationState.GREETING


class TestTrimHistory:
    def test_historico_pequeno_nao_altera(self):
        h = [{"role": "user", "content": "oi"}, {"role": "assistant", "content": "olá"}]
        assert trim_history(h) == h

    def test_historico_grande_e_truncado(self):
        h = []
        for i in range(30):
            h.append({"role": "user", "content": f"msg {i}"})
            h.append({"role": "assistant", "content": f"resp {i}"})
        trimmed = trim_history(h)
        assert len(trimmed) <= 20

    def test_historico_truncado_comeca_com_user(self):
        h = []
        for i in range(15):
            h.append({"role": "user", "content": f"u{i}"})
            h.append({"role": "assistant", "content": f"a{i}"})
        trimmed = trim_history(h)
        assert trimmed[0]["role"] == "user"


class TestExtractOrderTotal:
    def test_extrai_total_virgula(self):
        resp = "📦 Total: R$ 25,50"
        assert extract_order_total(resp) == 25.50

    def test_extrai_total_ponto(self):
        resp = "💰 Total: R$ 100.00"
        assert extract_order_total(resp) == 100.00

    def test_retorna_none_sem_total(self):
        assert extract_order_total("Olá, tudo bem?") is None

    def test_extrai_primeiro_valor(self):
        resp = "Coca R$ 10,00\nTotal: R$ 10,00"
        result = extract_order_total(resp)
        assert result == 10.00


# ── Testes da engine (com mocks) ─────────────────────────────────────────────

class TestConversationEngine:
    @pytest.fixture
    def mock_claude(self):
        claude = AsyncMock()
        claude.chat = AsyncMock(
            return_value=(
                "Olá! Bem-vindo ao FN Mercadinho 👋 O que posso fazer por você?",
                150,
            )
        )
        return claude

    @pytest.fixture
    def mock_whatsapp(self):
        wa = AsyncMock()
        wa.send_text = AsyncMock(return_value=True)
        wa.send_typing = AsyncMock()
        return wa

    @pytest.fixture
    def mock_business(self) -> BusinessConfig:
        return BusinessConfig(
            {
                "mercadinho": {"nome": "FN Test"},
                "horario": {"abertura": "00:00", "fechamento": "23:59", "dias": "Todos"},
                "delivery": {"tipo": "condominio", "blocos": ["A", "B"]},
                "pix": {"chave": "test@test.com", "tipo_chave": "email", "titular": "Teste"},
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
                },
            }
        )

    @pytest.fixture
    def inbound_message(self) -> InboundMessage:
        return InboundMessage(
            phone="5571999990001",
            name="Teste",
            text="Olá",
            message_id="MSG001",
            message_type=WhatsAppMessageType.TEXT,
            timestamp=1700000000,
        )

    async def test_cria_cliente_novo(
        self,
        db_session: AsyncSession,
        mock_claude,
        mock_whatsapp,
        mock_business,
        inbound_message,
    ):
        engine = ConversationEngine(
            db=db_session,
            claude=mock_claude,
            whatsapp=mock_whatsapp,
            business=mock_business,
        )
        await engine.handle(inbound_message)

        from sqlalchemy import select
        from app.models.customer import Customer
        result = await db_session.execute(
            select(Customer).where(Customer.phone == "5571999990001")
        )
        customer = result.scalar_one_or_none()
        assert customer is not None
        assert customer.name == "Teste"

    async def test_envia_resposta_via_whatsapp(
        self,
        db_session: AsyncSession,
        mock_claude,
        mock_whatsapp,
        mock_business,
        inbound_message,
    ):
        engine = ConversationEngine(
            db=db_session,
            claude=mock_claude,
            whatsapp=mock_whatsapp,
            business=mock_business,
        )
        await engine.handle(inbound_message)

        mock_whatsapp.send_text.assert_called_once()
        call_args = mock_whatsapp.send_text.call_args
        assert call_args[0][0] == "5571999990001"
        assert "Bem-vindo" in call_args[0][1]

    async def test_cria_conversa_nova(
        self,
        db_session: AsyncSession,
        mock_claude,
        mock_whatsapp,
        mock_business,
        inbound_message,
    ):
        from sqlalchemy import select
        from app.models.conversation import Conversation

        engine = ConversationEngine(
            db=db_session,
            claude=mock_claude,
            whatsapp=mock_whatsapp,
            business=mock_business,
        )
        await engine.handle(inbound_message)

        result = await db_session.execute(select(Conversation))
        convs = result.scalars().all()
        assert len(convs) == 1
        # Após greeting, estado avança para MAIN_MENU
        assert convs[0].state == ConversationState.MAIN_MENU

    async def test_persiste_mensagens(
        self,
        db_session: AsyncSession,
        mock_claude,
        mock_whatsapp,
        mock_business,
        inbound_message,
    ):
        from sqlalchemy import select
        from app.models.message import Message

        engine = ConversationEngine(
            db=db_session,
            claude=mock_claude,
            whatsapp=mock_whatsapp,
            business=mock_business,
        )
        await engine.handle(inbound_message)

        result = await db_session.execute(select(Message))
        msgs = result.scalars().all()
        assert len(msgs) == 2  # user + bot

    async def test_audio_nao_processado_envia_aviso(
        self,
        db_session: AsyncSession,
        mock_claude,
        mock_whatsapp,
        mock_business,
    ):
        audio_msg = InboundMessage(
            phone="5571999990002",
            name="Fulano",
            text="",
            message_id="AUDIO001",
            message_type=WhatsAppMessageType.AUDIO,
            timestamp=1700000000,
        )
        engine = ConversationEngine(
            db=db_session,
            claude=mock_claude,
            whatsapp=mock_whatsapp,
            business=mock_business,
        )
        await engine.handle(audio_msg)

        mock_claude.chat.assert_not_called()
        mock_whatsapp.send_text.assert_called_once()
        assert "texto" in mock_whatsapp.send_text.call_args[0][1].lower()
