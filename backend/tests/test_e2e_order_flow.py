"""
Testes E2E do fluxo completo de pedido via WhatsApp.

Simula a jornada completa:
  Cliente → GREETING → MAIN_MENU → ORDER_ITEMS → ORDER_CONFIRM
       → ORDER_DELIVERY → ORDER_PAYMENT → CLOSED
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import BusinessConfig
from app.core.conversation.engine import ConversationEngine
from app.core.whatsapp.types import InboundMessage, WhatsAppMessageType
from app.models.conversation import Conversation, ConversationState, ConversationStatus
from app.models.customer import Customer
from app.models.order import Order, OrderStatus


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def business() -> BusinessConfig:
    return BusinessConfig(
        {
            "mercadinho": {"nome": "FN Mercadinho"},
            "horario": {"abertura": "00:00", "fechamento": "23:59", "dias": "Todos"},
            "delivery": {
                "tipo": "condominio",
                "nome_condominio": "Residencial Teste",
                "blocos": ["A", "B", "C"],
                "taxa": 0,
                "pedido_minimo": 0,
                "tempo_estimado": "15-30 min",
            },
            "pix": {
                "chave": "test@fn.com",
                "tipo_chave": "email",
                "titular": "FN Mercadinho",
                "banco": "Nubank",
            },
            "catalogo": [
                {
                    "categoria": "Bebidas",
                    "produtos": [
                        {"nome": "Coca-Cola 2L", "preco": 10.00},
                        {"nome": "Água 500ml", "preco": 3.00},
                    ],
                }
            ],
            "personalidade": {
                "saudacao": "Olá! 👋",
                "despedida": "Tchau!",
                "quando_nao_entende": "Hm?",
                "quando_sem_estoque": "Sem estoque.",
                "quando_fora_area": "Fora da área.",
                "tratamento": "você",
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
def mock_whatsapp() -> AsyncMock:
    wa = AsyncMock()
    wa.send_text = AsyncMock(return_value=True)
    wa.send_typing = AsyncMock()
    return wa


def make_claude_mock(response: str, tokens: int = 100) -> AsyncMock:
    claude = AsyncMock()
    claude.chat = AsyncMock(return_value=(response, tokens))
    return claude


def make_msg(text: str, phone: str = "5571900000099") -> InboundMessage:
    return InboundMessage(
        phone=phone,
        name="Cliente E2E",
        text=text,
        message_id=f"msg_{text[:10]}",
        message_type=WhatsAppMessageType.TEXT,
        timestamp=1700000000,
    )


async def build_engine(db, claude_response, mock_wa, biz) -> ConversationEngine:
    return ConversationEngine(
        db=db,
        claude=make_claude_mock(claude_response),
        whatsapp=mock_wa,
        business=biz,
    )


# ── Testes E2E ────────────────────────────────────────────────────────────────

class TestFullOrderFlow:
    async def test_greeting_cria_cliente_e_conversa(
        self, db_session: AsyncSession, mock_whatsapp, business
    ):
        engine = await build_engine(
            db_session,
            "Olá! Bem-vindo ao FN Mercadinho 👋 O que posso fazer?\n1️⃣ Pedido",
            mock_whatsapp,
            business,
        )
        await engine.handle(make_msg("oi"))

        result = await db_session.execute(select(Customer).where(Customer.phone == "5571900000099"))
        customer = result.scalar_one_or_none()
        assert customer is not None

        result2 = await db_session.execute(select(Conversation))
        conv = result2.scalar_one_or_none()
        assert conv is not None
        assert conv.state == ConversationState.MAIN_MENU

    async def test_order_items_avanca_estado(
        self, db_session: AsyncSession, mock_whatsapp, business
    ):
        # Fase 1: greeting
        engine = await build_engine(db_session, "Bem-vindo! Menu:", mock_whatsapp, business)
        await engine.handle(make_msg("oi"))

        # Fase 2: seleciona pedido
        engine2 = await build_engine(
            db_session,
            "Claro! O que você deseja pedir? 😊",
            mock_whatsapp,
            business,
        )
        await engine2.handle(make_msg("1"))

        result = await db_session.execute(select(Conversation))
        conv = result.scalar_one_or_none()
        assert conv.state == ConversationState.ORDER_ITEMS

    async def test_order_confirm_extrai_itens_do_resumo(
        self, db_session: AsyncSession, mock_whatsapp, business
    ):
        # Chega até ORDER_ITEMS com 2 msgs
        engine1 = await build_engine(db_session, "Bem-vindo!", mock_whatsapp, business)
        await engine1.handle(make_msg("oi"))
        engine2 = await build_engine(db_session, "O que deseja?", mock_whatsapp, business)
        await engine2.handle(make_msg("1"))

        # Claude retorna resumo com itens
        resumo = (
            "📦 *Seu pedido:*\n"
            "  • Coca-Cola 2L x2 — R$ 20,00\n"
            "💰 *Total: R$ 20,00*\n"
            "Deseja confirmar?"
        )
        engine3 = await build_engine(db_session, resumo, mock_whatsapp, business)
        await engine3.handle(make_msg("2 cocas"))

        result = await db_session.execute(select(Conversation))
        conv = result.scalar_one_or_none()
        assert conv.state == ConversationState.ORDER_CONFIRM

        # Contexto deve ter os itens
        from app.core.orders.context import OrderContext
        ctx = OrderContext.from_json(conv.context_json)
        assert len(ctx.items) == 1
        assert ctx.items[0].name == "Coca-Cola 2L"
        assert ctx.items[0].qty == 2

    async def test_fluxo_completo_cria_order_no_bd(
        self, db_session: AsyncSession, mock_whatsapp, business
    ):
        """
        Simula o fluxo completo até ORDER_PAYMENT e verifica que o Order foi criado.
        """
        from app.core.orders.context import OrderContext

        phone = "5571900000099"

        # 1. Greeting → MAIN_MENU
        e = await build_engine(db_session, "Bem-vindo!", mock_whatsapp, business)
        await e.handle(make_msg("oi", phone))

        # 2. MAIN_MENU → ORDER_ITEMS
        e = await build_engine(db_session, "O que deseja?", mock_whatsapp, business)
        await e.handle(make_msg("1", phone))

        # 3. ORDER_ITEMS → ORDER_CONFIRM (Claude retorna resumo)
        resumo = (
            "📦 *Seu pedido:*\n"
            "  • Coca-Cola 2L x1 — R$ 10,00\n"
            "💰 *Total: R$ 10,00*\nConfirmar?"
        )
        e = await build_engine(db_session, resumo, mock_whatsapp, business)
        await e.handle(make_msg("quero uma coca", phone))

        # 4. ORDER_CONFIRM → ORDER_DELIVERY (Claude pede bloco)
        e = await build_engine(
            db_session,
            "Perfeito! Para delivery, qual bloco e apartamento?",
            mock_whatsapp,
            business,
        )
        await e.handle(make_msg("sim confirmo", phone))

        # 5. ORDER_DELIVERY → ORDER_PAYMENT (Claude retorna Pix)
        pix_msg = (
            "💰 Pagar via Pix\n"
            "Chave (email): `test@fn.com`\n"
            "Titular: FN Mercadinho\n"
            "Valor: R$ 10,00\n"
        )
        e = await build_engine(db_session, pix_msg, mock_whatsapp, business)
        await e.handle(make_msg("Bloco A, apto 201", phone))

        # Verifica estado da conversa
        result = await db_session.execute(
            select(Conversation).where(
                Conversation.status == ConversationStatus.ACTIVE
            )
        )
        conv = result.scalar_one_or_none()
        assert conv is not None
        assert conv.state == ConversationState.ORDER_PAYMENT

        # Verifica se Order foi criado no BD
        ctx = OrderContext.from_json(conv.context_json)
        assert ctx.order_id is not None

        import uuid as _uuid
        order_result = await db_session.execute(
            select(Order).where(Order.id == _uuid.UUID(ctx.order_id))
        )
        order = order_result.scalar_one_or_none()
        assert order is not None
        assert order.status == OrderStatus.PENDING
        assert float(order.total_amount) == 10.0
        assert order.delivery_building_block == "A"
        assert order.delivery_apartment == "201"

    async def test_cliente_bloqueado_nao_atendido(
        self, db_session: AsyncSession, mock_whatsapp, business
    ):
        # Cria cliente bloqueado
        customer = Customer(phone="5571900000099", name="Bloqueado", is_blocked=True)
        db_session.add(customer)
        await db_session.flush()

        engine = await build_engine(db_session, "Olá!", mock_whatsapp, business)
        await engine.handle(make_msg("oi"))

        mock_whatsapp.send_text.assert_not_called()

    async def test_audio_recebe_aviso(
        self, db_session: AsyncSession, mock_whatsapp, business
    ):
        audio_msg = InboundMessage(
            phone="5571900000099",
            name="Teste",
            text="",
            message_id="audio1",
            message_type=WhatsAppMessageType.AUDIO,
            timestamp=1700000000,
        )
        engine = await build_engine(db_session, "", mock_whatsapp, business)
        await engine.handle(audio_msg)

        mock_whatsapp.send_text.assert_called_once()
        assert "texto" in mock_whatsapp.send_text.call_args[0][1].lower()
