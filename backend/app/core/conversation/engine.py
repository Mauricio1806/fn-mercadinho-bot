"""Motor de conversa — orquestra estados, Claude e WhatsApp."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import BusinessConfig, get_business_config
from app.core.ai.claude_client import ClaudeClient, get_claude_client
from app.core.ai.prompt_builder import build_system_prompt
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


class ConversationEngine:
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

        from app.api.middleware.rate_limit import is_rate_limited
        rl = await is_rate_limited(message.phone)
        print("RATE_LIMITED:", rl, flush=True)
        if rl:
            logger.warning("Rate limit: ignorando mensagem de %s", message.phone)
            return

        customer = await self._get_or_create_customer(message)

        if customer.is_blocked:
            logger.info("Cliente bloqueado ignorado: %s", message.phone)
            return

        conversation = await self._get_or_create_conversation(customer)

        # Imagem ou PDF em estado de pagamento → comprovante PIX
        print(f"MEDIA CHECK: image_url={bool(message.image_url)} type={message.message_type.value} state={conversation.state.value}", flush=True)
        if (
            message.image_url
            and message.message_type.value in ("image", "document")
        ):
            await self._process_payment_receipt(message, customer, conversation)
            return

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

        order_ctx = OrderContext.from_json(conversation.context_json)
        history = self._build_history(conversation)
        system_prompt = build_system_prompt(conversation.state, self._business)
        augmented_message = self._augment_message(message.text, conversation.state, order_ctx)

        print("CALLING CLAUDE...", flush=True)

        # Passa a função de busca para o Claude usar via tool use
        ai_response, tokens = await self._claude.chat(
            system_prompt=system_prompt,
            history=history,
            user_message=augmented_message,
            product_search_fn=self._search_products,
        )

        validation = validate_response(ai_response, conversation.state, order_ctx, self._business)
        ai_response = validation.safe_response

        order_ctx = self._update_order_context(
            order_ctx, conversation.state, ai_response, message.text
        )

        next_state = next_state_from_response(
            conversation.state, ai_response, message.text
        )

        if (
            next_state in (ConversationState.ORDER_PAYMENT, ConversationState.PAYMENT_RECEIPT, ConversationState.CLOSED)
            and conversation.state not in (ConversationState.ORDER_PAYMENT, ConversationState.PAYMENT_RECEIPT, ConversationState.CLOSED)
            and not order_ctx.order_id
            and order_ctx.items
        ):
            order_ctx = await self._finalize_order(customer, order_ctx)

        await self._save_messages(
            conversation=conversation,
            user_text=message.text,
            bot_text=ai_response,
            tokens=tokens,
            whatsapp_msg_id=message.message_id,
        )

        conversation.context_json = order_ctx.to_json()
        await self._update_conversation_state(conversation, next_state)

        await ws_manager.broadcast_conversation_update(
            conversation_id=str(conversation.id),
            message_content=ai_response,
            direction="outbound",
            is_ai_generated=True,
            tokens_used=tokens,
        )

        await self._whatsapp.send_typing(message.phone, duration_ms=1500)
        print("SENDING:", message.phone, ai_response[:50], flush=True)

        # Se entrou em ORDER_PAYMENT agora, envia Pix automaticamente — ignora resposta do Claude
        if next_state == ConversationState.ORDER_PAYMENT or conversation.state == ConversationState.ORDER_PAYMENT:
            b = self._business
            total = order_ctx.total or 0.0
            pix_msg = (
                f"Pague via Pix 💰\n"
                f"Chave {b.pix_tipo_chave.upper()}: {b.pix_chave}\n"
                f"Titular: {b.pix_titular} ({b.pix_banco})\n"
                f"Valor: R$ {total:.2f}\n\n"
                f"Apos pagar, manda o comprovante aqui pra gente confirmar e separar seu pedido! "
                f"Tempo estimado: 15 a 30 minutos 👍"
            )
            await self._whatsapp.send_text(message.phone, pix_msg)
        elif conversation.state == ConversationState.PAYMENT_RECEIPT:
            # Cliente esta aguardando — so reenvia o Pix se pedir, sem EMV
            b = self._business
            total = order_ctx.total or 0.0
            pix_msg = (
                f"Pague via Pix 💰\n"
                f"Chave {b.pix_tipo_chave.upper()}: {b.pix_chave}\n"
                f"Titular: {b.pix_titular} ({b.pix_banco})\n"
                f"Valor: R$ {total:.2f}\n\n"
                f"Apos pagar, manda o comprovante aqui (foto ou PDF do banco)!"
            )
            pix_keywords = re.compile(r"pix|codigo|chave|pagar|pagamento", re.IGNORECASE)
            if pix_keywords.search(message.text or ""):
                await self._whatsapp.send_text(message.phone, pix_msg)
            else:
                await self._whatsapp.send_text(message.phone, ai_response)
        else:
            await self._whatsapp.send_text(message.phone, ai_response)

        logger.info(
            "Atendimento: customer=%s state=%s→%s tokens=%d",
            message.phone,
            conversation.state,
            next_state,
            tokens,
        )

    # ── Busca de produtos via tool use ────────────────────────────────────────

    async def _search_products(self, termo: str) -> str:
        """Executada pelo Claude via tool use quando precisa buscar um produto."""
        try:
            from app.database.session import AsyncSessionLocal
            palavras = [p for p in termo.lower().split() if len(p) >= 3]
            seen = set()
            rows = []

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("""
                        SELECT p.name, p.price, pc.name as category
                        FROM products p
                        JOIN product_categories pc ON p.category_id = pc.id
                        WHERE p.is_available = true AND p.name ILIKE :q
                        ORDER BY p.name LIMIT 15
                    """), {"q": f"%{termo}%"}
                )
                for row in result.fetchall():
                    if row.name not in seen:
                        seen.add(row.name)
                        rows.append(row)

                for palavra in palavras:
                    if len(rows) >= 15:
                        break
                    result = await session.execute(
                        text("""
                            SELECT p.name, p.price, pc.name as category
                            FROM products p
                            JOIN product_categories pc ON p.category_id = pc.id
                            WHERE p.is_available = true AND p.name ILIKE :q
                            ORDER BY p.name LIMIT 10
                        """), {"q": f"%{palavra}%"}
                    )
                    for row in result.fetchall():
                        if row.name not in seen:
                            seen.add(row.name)
                            rows.append(row)

            if not rows:
                return f"Nenhum produto encontrado para '{termo}'. Tente um termo diferente."

            lines = [f"Produtos encontrados para '{termo}':"]
            for row in rows[:15]:
                lines.append(f"- {row.name}: R$ {float(row.price):.2f} ({row.category})")
            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Erro ao buscar produtos ('{termo}'): {e}")
            return f"Erro temporario ao buscar '{termo}'. Tente novamente."


    async def _is_allowed(self, message: InboundMessage) -> bool:
        if not message.is_text():
            if message.message_type.value in ("audio", "image"):
                await self._whatsapp.send_text(
                    message.phone,
                    "Por enquanto so consigo ler mensagens de texto 😊 Pode digitar o que precisar?",
                )
            return False

                # atendimento 24/7
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
        if state in (ConversationState.ORDER_ITEMS, ConversationState.ORDER_CONFIRM):
            parsed_items = parse_items_from_claude(ai_response)
            if parsed_items:
                ctx.items = parsed_items
                ctx.recalculate_total()

            total = extract_order_total(ai_response)
            if total and total > 0:
                ctx.total = total

            ctx.delivery_type = parse_delivery_type(user_message)

        elif state == ConversationState.ORDER_DELIVERY:
            block, apt = extract_block_and_apartment(user_message)
            if block:
                ctx.building_block = block
            if apt:
                ctx.apartment = apt

        return ctx

    async def _finalize_order(
        self, customer: Customer, order_ctx: OrderContext
    ) -> OrderContext:
        try:
            if order_ctx.delivery_type == "delivery" and order_ctx.building_block:
                validation = validate_delivery(
                    order_ctx.building_block,
                    order_ctx.apartment or "",
                    self._business,
                )
                if not validation.is_valid:
                    logger.warning("Delivery invalido: %s", validation.error_message)

            service = OrderService(self._db)
            order = await service.create_from_context(customer, order_ctx)
            order_ctx.order_id = str(order.id)

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
        order_ctx = OrderContext.from_json(conversation.context_json)
        expected_total = order_ctx.total or 0.0
        # Se total zerado, busca do ultimo pedido do cliente no banco
        if not expected_total and order_ctx.order_id:
            from sqlalchemy import select as _select
            import uuid as _uuid
            from app.models.order import Order as _Order
            try:
                _r = await self._db.execute(_select(_Order).where(_Order.id == _uuid.UUID(order_ctx.order_id)))
                _o = _r.scalar_one_or_none()
                if _o:
                    expected_total = float(_o.total_amount)
            except Exception:
                pass

        order_ctx = OrderContext.from_json(conversation.context_json)
        if not order_ctx.order_id and order_ctx.items:
            order_ctx = await self._finalize_order(customer, order_ctx)
            conversation.context_json = order_ctx.to_json()
            await self._db.flush()

        await self._whatsapp.send_typing(message.phone, duration_ms=3000)

        validation = await validate_pix_receipt(
            image_url=message.image_url,
            expected_amount=expected_total,
            claude=self._claude,
            business=self._business,
            db=self._db,
            order_id=order_ctx.order_id,
            customer_phone=customer.phone,
        )

        if validation.is_valid:
            reply = (
                "Comprovante confirmado! Obrigado! 🎉\n\n"
                "Seu pedido ja esta sendo separado!\n"
                "Em breve voce recebera a entrega. Qualquer duvida e so chamar 😊"
            )
            await self._whatsapp.send_text(message.phone, reply)

            if order_ctx.order_id:
                await self._mark_order_payment_confirmed(
                    order_ctx.order_id,
                    customer,
                    conversation,
                )

            await self._update_conversation_state(conversation, ConversationState.CLOSED)

        else:
            if validation.fraud_result and validation.fraud_result.flags:
                reply = validation.reason
            else:
                reply = (
                    "Nao consegui validar o comprovante.\n\n"
                    f"Detalhe: {validation.reason}\n\n"
                    "Pode reenviar o comprovante? Certifique que mostra:\n"
                    f"Valor: R$ {expected_total:.2f}\n"
                    f"Chave PIX: {self._business.pix_chave}"
                )
            await self._whatsapp.send_text(message.phone, reply)
            await self._update_conversation_state(
                conversation, ConversationState.PAYMENT_RECEIPT
            )

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

            await ws_manager.broadcast_conversation_update(
                conversation_id=str(conversation.id),
                message_content=f"[VENDA_CONFIRMADA] Pedido {order_id[:8].upper()} — R$ {order.total_amount:.2f}",
                direction="outbound",
                is_ai_generated=False,
                tokens_used=0,
            )

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
