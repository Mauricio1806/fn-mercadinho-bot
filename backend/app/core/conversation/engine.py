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
from sqlalchemy import text
from app.core.ai.response_validator import validate_response
from app.core.conversation.handlers import (
    extract_order_total,
    next_state_from_response,
    trim_history,
)
from app.core.notifications.notify_owner import notify_new_order, notify_sale_confirmed
from app.core.payments.receipt_validator import validate_pix_receipt
from app.services.pix_fraud_guard import FRAUD_RESPONSES, detect_pressure
from app.core.orders.context import OrderContext
from app.core.orders.delivery_validator import extract_block_and_apartment, validate_delivery
from app.core.orders.parser import parse_delivery_type, parse_items_from_claude
from app.core.orders.service import OrderService
from app.core.whatsapp.client import WhatsAppClient, get_whatsapp_client
from app.core.ws_manager import ws_manager
from app.core.whatsapp.types import InboundMessage
from app.models.conversation import Conversation, ConversationState, ConversationStatus
from app.models.customer import Customer
from app.models.message import Message, MessageDirection, MessageType
from app.models.order import Order, OrderStatus

logger = logging.getLogger(__name__)


# Cache do catálogo — evita buscar no banco a cada mensagem
_catalog_cache: str = ""
_catalog_cache_time: float = 0.0
_CATALOG_CACHE_TTL = 300  # 5 minutos


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
        print("ENGINE HANDLE:", message.phone, message.text, flush=True)
        """Ponto de entrada principal — processa uma mensagem recebida."""

        # Rate limiting por número
        from app.api.middleware.rate_limit import is_rate_limited
        rl = await is_rate_limited(message.phone)
        print("RATE_LIMITED:", rl, flush=True)
        if rl:
            logger.warning("Rate limit: ignorando mensagem de %s", message.phone)
            return

        # Obtém ou cria cliente e conversa antes de qualquer decisão de tipo
        customer = await self._get_or_create_customer(message)

        if customer.is_blocked:
            logger.info("Cliente bloqueado ignorado: %s", message.phone)
            return

        conversation = await self._get_or_create_conversation(customer)

        # Imagem ou PDF em estado de pagamento → trata como comprovante PIX
        print(f"MEDIA CHECK: image_url={bool(message.image_url)} type={message.message_type.value} state={conversation.state.value}", flush=True)
        if (
            message.image_url
            and message.message_type.value in ("image", "document")
            and conversation.state in (
                ConversationState.ORDER_PAYMENT,
                ConversationState.PAYMENT_RECEIPT,
            )
        ):
            await self._process_payment_receipt(message, customer, conversation)
            return

        # Verifica tipo (bloqueia outras mídias) e horário
        if not await self._is_allowed(message):
            return

        # Detecta pressão para liberar pedido sem comprovante
        if (
            conversation.state == ConversationState.PAYMENT_RECEIPT
            and message.text
            and detect_pressure(message.text)
        ):
            await self._whatsapp.send_text(
                message.phone, FRAUD_RESPONSES["PRESSAO_DETECTADA"]
            )
            return

        # Carrega contexto do pedido
        order_ctx = OrderContext.from_json(conversation.context_json)

        # Carrega histórico de mensagens
        history = self._build_history(conversation)

        # System prompt baseado no estado atual
        catalog_text = await self._get_catalog_text()
        system_prompt = build_system_prompt(conversation.state, self._business, catalog_text=catalog_text)

        # Monta mensagem aumentada com contexto quando em estados de pedido
        augmented_message = self._augment_message(message.text, conversation.state, order_ctx)

        # Chama Claude
        print("CALLING CLAUDE...", flush=True)
        ai_response, tokens = await self._claude.chat(
            system_prompt=system_prompt,
            history=history,
            user_message=augmented_message,
        )

        # ── Checkpoint de qualidade ──────────────────────────────────────────
        validation = validate_response(ai_response, conversation.state, order_ctx, self._business)
        ai_response = validation.safe_response
        # ─────────────────────────────────────────────────────────────────────

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

        # Broadcast WebSocket — painel recebe a mensagem em tempo real
        await ws_manager.broadcast_conversation_update(
            conversation_id=str(conversation.id),
            message_content=ai_response,
            direction="outbound",
            is_ai_generated=True,
            tokens_used=tokens,
        )

        # Envia resposta ao cliente
        await self._whatsapp.send_typing(message.phone, duration_ms=1500)
        print("SENDING:", message.phone, ai_response[:50], flush=True)
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

    async def _process_payment_receipt(
        self,
        message: InboundMessage,
        customer: Customer,
        conversation: Conversation,
    ) -> None:
        """
        Processa comprovante PIX enviado pelo cliente.
        - Valida via Claude Vision
        - Se válido: confirma venda, notifica donos, broadcast dashboard
        - Se inválido: pede reenvio
        """
        order_ctx = OrderContext.from_json(conversation.context_json)
        expected_total = order_ctx.total or 0.0

        await self._whatsapp.send_typing(message.phone, duration_ms=3000)

        validation = await validate_pix_receipt(
            image_url=message.image_url,  # type: ignore[arg-type]
            expected_amount=expected_total,
            claude=self._claude,
            business=self._business,
            db=self._db,
            order_id=order_ctx.order_id,
            customer_phone=customer.phone,
        )

        if validation.is_valid:
            reply = (
                "✅ *Comprovante confirmado!* Obrigado! 🎉\n\n"
                "📦 Seu pedido já está sendo separado!\n"
                "Em breve você receberá a entrega. Qualquer dúvida é só chamar 😊"
            )
            await self._whatsapp.send_text(message.phone, reply)

            # Atualiza pedido no banco
            if order_ctx.order_id:
                await self._mark_order_payment_confirmed(
                    order_ctx.order_id,
                    customer,
                    conversation,
                )

            # Fecha conversa
            await self._update_conversation_state(conversation, ConversationState.CLOSED)

        else:
            # fraud_result tem mensagem específica; sem ele usa formato padrão
            if validation.fraud_result and validation.fraud_result.flags:
                reply = validation.reason
            else:
                reply = (
                    "😕 Não consegui validar o comprovante.\n\n"
                    f"Detalhe: {validation.reason}\n\n"
                    "Pode reenviar o comprovante? Certifique que mostra:\n"
                    f"• Valor: *R$ {expected_total:.2f}*\n"
                    f"• Chave PIX: *{self._business.pix_chave}*"
                )
            await self._whatsapp.send_text(message.phone, reply)
            await self._update_conversation_state(
                conversation, ConversationState.PAYMENT_RECEIPT
            )

        # Salva mensagem do cliente no histórico
        self._db.add(Message(
            conversation_id=conversation.id,
            direction=MessageDirection.INBOUND,
            message_type=MessageType.IMAGE,
            content="[Comprovante PIX enviado]",
            whatsapp_message_id=message.message_id,
            is_ai_generated=False,
        ))
        self._db.add(Message(
            conversation_id=conversation.id,
            direction=MessageDirection.OUTBOUND,
            message_type=MessageType.TEXT,
            content=reply,
            is_ai_generated=True,
            tokens_used=0,
        ))
        await self._db.flush()

    async def _mark_order_payment_confirmed(
        self,
        order_id: str,
        customer: Customer,
        conversation: Conversation,
    ) -> None:
        """Marca o pedido como pago e notifica os donos."""
        from sqlalchemy import select as sa_select
        import uuid as _uuid

        try:
            result = await self._db.execute(
                sa_select(Order).where(Order.id == _uuid.UUID(order_id))
            )
            order = result.scalar_one_or_none()
            if not order:
                return

            commission = float(order.total_amount) * (self._business.comissao_percentual / 100)
            order.status = OrderStatus.PAYMENT_CONFIRMED
            order.pix_confirmed = True
            order.commission_amount = commission
            await self._db.flush()

            # Broadcast para o dashboard em tempo real
            await ws_manager.broadcast_conversation_update(
                conversation_id=str(conversation.id),
                message_content=f"[VENDA_CONFIRMADA] Pedido {order_id[:8].upper()} — R$ {order.total_amount:.2f}",
                direction="outbound",
                is_ai_generated=False,
                tokens_used=0,
            )

            # Notifica os dois donos
            await notify_sale_confirmed(
                order=order,
                customer_phone=customer.phone,
                customer_name=customer.name,
                commission_amount=commission,
                whatsapp=self._whatsapp,
                business=self._business,
            )

        except Exception:
            logger.exception("Erro ao confirmar pagamento do pedido %s", order_id)

    async def _update_conversation_state(
        self, conversation: Conversation, new_state: ConversationState
    ) -> None:
        conversation.state = new_state
        if new_state == ConversationState.CLOSED:
            conversation.status = ConversationStatus.CLOSED
        await self._db.flush()

    async def _get_catalog_text(self) -> str:
        import time
        global _catalog_cache, _catalog_cache_time
        if _catalog_cache and (time.time() - _catalog_cache_time) < _CATALOG_CACHE_TTL:
            return _catalog_cache
        try:
            from app.database.session import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("SELECT p.name, p.price, pc.name as category FROM products p JOIN product_categories pc ON p.category_id = pc.id WHERE p.is_available = true ORDER BY pc.name, p.name")
                )
                rows = result.fetchall()
            lines = []
            current_cat = None
            for row in rows:
                if row.category != current_cat:
                    current_cat = row.category
                    lines.append(f"[{current_cat}]")
                lines.append(f"{row.name}|R${float(row.price):.2f}")
            _catalog_cache = "\n".join(lines)
            _catalog_cache_time = time.time()
            return _catalog_cache
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Erro ao buscar catálogo: {e}")
            return _catalog_cache or ""
