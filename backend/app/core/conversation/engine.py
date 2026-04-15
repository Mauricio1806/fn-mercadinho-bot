"""Motor de conversa — orquestra estados, Claude e WhatsApp."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import BusinessConfig, get_business_config
from app.core.ai.claude_client import ClaudeClient, get_claude_client
from app.core.ai.prompt_builder import build_system_prompt
from app.core.conversation.handlers import (
    extract_order_total,
    next_state_from_response,
    trim_history,
)
from app.core.notifications.notify_owner import notify_new_order
from app.core.orders.context import OrderContext
from app.core.orders.delivery_validator import extract_block_and_apartment, validate_delivery
from app.core.orders.parser import parse_delivery_type, parse_items_from_claude
from app.core.orders.service import OrderService
from app.core.whatsapp.client import WhatsAppClient, get_whatsapp_client
from app.core.whatsapp.types import InboundMessage
from app.models.conversation import Conversation, ConversationState, ConversationStatus
from app.models.customer import Customer
from app.models.message import Message, MessageDirection, MessageType

logger = logging.getLogger(__name__)


class ConversationEngine:
    """
    Orquestra o fluxo completo de atendimento:
    1. Rate limit check
    2. Identifica/cria cliente
    3. Carrega/cria conversa ativa
    4. Chama Claude com histórico + system prompt do estado
    5. Extrai contexto do pedido da resposta
    6. Atualiza estado da máquina
    7. Cria Order no BD quando chega em ORDER_PAYMENT
    8. Persiste mensagens
    9. Envia resposta via WhatsApp
    """

    def __init__(
        self,
        db: AsyncSession,
        claude: ClaudeClient | None = None,
        whatsapp: WhatsAppClient | None = None,
        business: BusinessConfig | None = None,
    ) -> None:
        self._db = db
        self._claude = claude or get_claude_client()
        self._whatsapp = whatsapp or get_whatsapp_client()
        self._business = business or get_business_config()

    async def handle(self, message: InboundMessage) -> None:
        """Ponto de entrada principal — processa uma mensagem recebida."""

        # Rate limiting por número
        from app.api.middleware.rate_limit import is_rate_limited
        if await is_rate_limited(message.phone):
            logger.warning("Rate limit: ignorando mensagem de %s", message.phone)
            return

        # Verifica tipo e horário
        if not await self._is_allowed(message):
            return

        # Obtém ou cria cliente
        customer = await self._get_or_create_customer(message)

        if customer.is_blocked:
            logger.info("Cliente bloqueado ignorado: %s", message.phone)
            return

        # Obtém ou cria conversa ativa
        conversation = await self._get_or_create_conversation(customer)

        # Carrega contexto do pedido
        order_ctx = OrderContext.from_json(conversation.context_json)

        # Carrega histórico de mensagens
        history = self._build_history(conversation)

        # System prompt baseado no estado atual
        system_prompt = build_system_prompt(conversation.state, self._business)

        # Monta mensagem aumentada com contexto quando em estados de pedido
        augmented_message = self._augment_message(message.text, conversation.state, order_ctx)

        # Chama Claude
        ai_response, tokens = await self._claude.chat(
            system_prompt=system_prompt,
            history=history,
            user_message=augmented_message,
        )

        # Atualiza contexto do pedido com base na resposta do Claude
        order_ctx = self._update_order_context(
            order_ctx, conversation.state, ai_response, message.text
        )

        # Determina próximo estado
        next_state = next_state_from_response(
            conversation.state, ai_response, message.text
        )

        # Ação especial: cria o pedido no BD quando atinge ORDER_PAYMENT
        if (
            next_state == ConversationState.ORDER_PAYMENT
            and conversation.state != ConversationState.ORDER_PAYMENT
            and not order_ctx.order_id
            and order_ctx.items
        ):
            order_ctx = await self._finalize_order(customer, order_ctx)

        # Persiste mensagens e contexto
        await self._save_messages(
            conversation=conversation,
            user_text=message.text,
            bot_text=ai_response,
            tokens=tokens,
            whatsapp_msg_id=message.message_id,
        )

        # Atualiza estado e contexto da conversa
        conversation.context_json = order_ctx.to_json()
        await self._update_conversation_state(conversation, next_state)

        # Envia resposta ao cliente
        await self._whatsapp.send_typing(message.phone, duration_ms=1500)
        await self._whatsapp.send_text(message.phone, ai_response)

        logger.info(
            "Atendimento: customer=%s state=%s→%s tokens=%d",
            message.phone,
            conversation.state,
            next_state,
            tokens,
        )

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _is_allowed(self, message: InboundMessage) -> bool:
        """Verifica tipo de mensagem e horário de funcionamento."""
        if not message.is_text():
            if message.message_type.value in ("audio", "image"):
                await self._whatsapp.send_text(
                    message.phone,
                    "Por enquanto só consigo ler mensagens de texto 😊 Pode digitar o que precisar?",
                )
            return False

        now = datetime.now(timezone.utc)
        try:
            abertura_h, abertura_m = map(int, self._business.horario_abertura.split(":"))
            fechamento_h, fechamento_m = map(int, self._business.horario_fechamento.split(":"))

            # Hora de Brasília (UTC-3)
            hora_brasilia = (now.hour - 3) % 24
            hora_atual = hora_brasilia * 60 + now.minute
            hora_abre = abertura_h * 60 + abertura_m
            hora_fecha = fechamento_h * 60 + fechamento_m

            if hora_atual < hora_abre or hora_atual >= hora_fecha:
                await self._whatsapp.send_text(
                    message.phone, self._business.msg_fora_horario
                )
                return False
        except Exception:
            pass

        return True

    async def _get_or_create_customer(self, message: InboundMessage) -> Customer:
        result = await self._db.execute(
            select(Customer).where(Customer.phone == message.phone)
        )
        customer = result.scalar_one_or_none()

        if not customer:
            customer = Customer(phone=message.phone, name=message.name)
            self._db.add(customer)
            await self._db.flush()
            logger.info("Novo cliente: %s", message.phone)
        elif message.name and not customer.name:
            customer.name = message.name

        return customer

    async def _get_or_create_conversation(self, customer: Customer) -> Conversation:
        result = await self._db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.customer_id == customer.id,
                Conversation.status == ConversationStatus.ACTIVE,
            )
            .order_by(Conversation.created_at.desc())
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = Conversation(
                customer_id=customer.id,
                status=ConversationStatus.ACTIVE,
                state=ConversationState.GREETING,
            )
            self._db.add(conversation)
            await self._db.flush()

        return conversation

    def _build_history(self, conversation: Conversation) -> list[dict[str, str]]:
        """Histórico sem lazy load — usa __dict__ para nova conversa."""
        messages = conversation.__dict__.get("messages", []) or []
        history = []
        for msg in messages:
            role = "user" if msg.direction == MessageDirection.INBOUND else "assistant"
            history.append({"role": role, "content": msg.content})
        return trim_history(history)

    def _augment_message(
        self,
        user_text: str,
        state: ConversationState,
        order_ctx: OrderContext,
    ) -> str:
        """Adiciona contexto do pedido à mensagem quando relevante."""
        if state == ConversationState.ORDER_DELIVERY and order_ctx.items:
            return (
                f"{user_text}\n\n"
                f"[CONTEXTO INTERNO: Pedido atual: {order_ctx.format_summary()}]"
            )
        return user_text

    def _update_order_context(
        self,
        ctx: OrderContext,
        state: ConversationState,
        ai_response: str,
        user_message: str,
    ) -> OrderContext:
        """Extrai e atualiza contexto do pedido a partir da resposta do Claude."""

        if state in (ConversationState.ORDER_ITEMS, ConversationState.ORDER_CONFIRM):
            # Tenta extrair itens do resumo do Claude
            parsed_items = parse_items_from_claude(ai_response)
            if parsed_items:
                ctx.items = parsed_items
                ctx.recalculate_total()

            # Total explícito
            total = extract_order_total(ai_response)
            if total and total > 0:
                ctx.total = total

            # Tipo de entrega
            ctx.delivery_type = parse_delivery_type(user_message)

        elif state == ConversationState.ORDER_DELIVERY:
            # Tenta extrair bloco e apartamento da mensagem do cliente
            block, apt = extract_block_and_apartment(user_message)
            if block:
                ctx.building_block = block
            if apt:
                ctx.apartment = apt

        return ctx

    async def _finalize_order(
        self, customer: Customer, order_ctx: OrderContext
    ) -> OrderContext:
        """Cria o Order real no banco de dados."""
        try:
            # Valida delivery se necessário
            if order_ctx.delivery_type == "delivery" and order_ctx.building_block:
                validation = validate_delivery(
                    order_ctx.building_block,
                    order_ctx.apartment or "",
                    self._business,
                )
                if not validation.is_valid:
                    logger.warning("Delivery inválido: %s", validation.error_message)
                    # Não bloqueia o fluxo — Claude já tratou isso

            service = OrderService(self._db)
            order = await service.create_from_context(customer, order_ctx)
            order_ctx.order_id = str(order.id)

            # Notifica donos
            await notify_new_order(
                order=order,
                customer_phone=customer.phone,
                customer_name=customer.name,
                whatsapp=self._whatsapp,
                business=self._business,
            )

            logger.info("Order %s criado e donos notificados.", order.id)

        except Exception:
            logger.exception("Erro ao criar Order no BD — fluxo continua")

        return order_ctx

    async def _save_messages(
        self,
        conversation: Conversation,
        user_text: str,
        bot_text: str,
        tokens: int,
        whatsapp_msg_id: str,
    ) -> None:
        self._db.add(Message(
            conversation_id=conversation.id,
            direction=MessageDirection.INBOUND,
            message_type=MessageType.TEXT,
            content=user_text,
            whatsapp_message_id=whatsapp_msg_id,
            is_ai_generated=False,
        ))
        self._db.add(Message(
            conversation_id=conversation.id,
            direction=MessageDirection.OUTBOUND,
            message_type=MessageType.TEXT,
            content=bot_text,
            is_ai_generated=True,
            tokens_used=tokens,
        ))
        await self._db.flush()

    async def _update_conversation_state(
        self, conversation: Conversation, new_state: ConversationState
    ) -> None:
        conversation.state = new_state
        if new_state == ConversationState.CLOSED:
            conversation.status = ConversationStatus.CLOSED
        await self._db.flush()
