"""Motor de conversa — orquestra estados, Claude e WhatsApp."""

from __future__ import annotations

import json
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
from app.core.whatsapp.client import WhatsAppClient, get_whatsapp_client
from app.core.whatsapp.types import InboundMessage
from app.models.conversation import Conversation, ConversationState, ConversationStatus
from app.models.customer import Customer
from app.models.message import Message, MessageDirection, MessageType

logger = logging.getLogger(__name__)


class ConversationEngine:
    """
    Orquestra o fluxo completo de atendimento:
    1. Identifica/cria cliente
    2. Carrega/cria conversa ativa
    3. Chama Claude com histórico + system prompt do estado
    4. Atualiza estado da máquina
    5. Persiste mensagens
    6. Envia resposta via WhatsApp
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

        # Verifica bloqueio e horário antes de qualquer coisa
        if not await self._is_allowed(message):
            return

        # Obtém ou cria cliente
        customer = await self._get_or_create_customer(message)

        if customer.is_blocked:
            logger.info("Cliente bloqueado ignorado: %s", message.phone)
            return

        # Obtém ou cria conversa ativa
        conversation = await self._get_or_create_conversation(customer)

        # Carrega histórico de mensagens
        history = self._build_history(conversation)

        # System prompt baseado no estado atual
        system_prompt = build_system_prompt(conversation.state, self._business)

        # Chama Claude
        ai_response, tokens = await self._claude.chat(
            system_prompt=system_prompt,
            history=history,
            user_message=message.text,
        )

        # Determina próximo estado
        next_state = next_state_from_response(
            conversation.state, ai_response, message.text
        )

        # Persiste mensagens
        await self._save_messages(
            conversation=conversation,
            user_text=message.text,
            bot_text=ai_response,
            tokens=tokens,
            whatsapp_msg_id=message.message_id,
        )

        # Atualiza estado da conversa
        await self._update_conversation_state(conversation, next_state)

        # Envia resposta ao cliente (typing + texto)
        await self._whatsapp.send_typing(message.phone, duration_ms=1500)
        await self._whatsapp.send_text(message.phone, ai_response)

        logger.info(
            "Atendimento: customer=%s state=%s→%s tokens=%d",
            message.phone,
            conversation.state,
            next_state,
            tokens,
        )

    async def _is_allowed(self, message: InboundMessage) -> bool:
        """Verifica se o atendimento está dentro do horário."""
        if not message.is_text():
            # Não processamos áudio/imagem por enquanto
            if message.message_type.value in ("audio", "image"):
                await self._whatsapp.send_text(
                    message.phone,
                    "Por enquanto só consigo ler mensagens de texto 😊 Pode digitar o que precisar?",
                )
            return False

        now = datetime.now(timezone.utc)
        # Converte horários do business.yaml para hoje
        try:
            abertura_h, abertura_m = map(int, self._business.horario_abertura.split(":"))
            fechamento_h, fechamento_m = map(int, self._business.horario_fechamento.split(":"))

            # Usa horário de Brasília (UTC-3)
            hora_brasilia = (now.hour - 3) % 24
            minuto = now.minute

            hora_atual = hora_brasilia * 60 + minuto
            hora_abre = abertura_h * 60 + abertura_m
            hora_fecha = fechamento_h * 60 + fechamento_m

            if hora_atual < hora_abre or hora_atual >= hora_fecha:
                await self._whatsapp.send_text(
                    message.phone, self._business.msg_fora_horario
                )
                return False
        except Exception:
            pass  # Se falhar na verificação de horário, permite atendimento

        return True

    async def _get_or_create_customer(self, message: InboundMessage) -> Customer:
        result = await self._db.execute(
            select(Customer).where(Customer.phone == message.phone)
        )
        customer = result.scalar_one_or_none()

        if not customer:
            customer = Customer(
                phone=message.phone,
                name=message.name,
            )
            self._db.add(customer)
            await self._db.flush()
            logger.info("Novo cliente criado: %s", message.phone)

        elif message.name and not customer.name:
            customer.name = message.name

        return customer

    async def _get_or_create_conversation(self, customer: Customer) -> Conversation:
        """Retorna conversa ativa ou cria uma nova."""
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
            logger.info("Nova conversa criada para %s", customer.phone)

        return conversation

    def _build_history(self, conversation: Conversation) -> list[dict[str, str]]:
        """Constrói histórico de mensagens no formato esperado pelo Claude."""
        # Acessa __dict__ diretamente para evitar lazy load em contexto async.
        # Se messages não estiver carregado (nova conversa), retorna vazio.
        messages = conversation.__dict__.get("messages", []) or []

        history = []
        for msg in messages:
            role = "user" if msg.direction == MessageDirection.INBOUND else "assistant"
            history.append({"role": role, "content": msg.content})

        return trim_history(history)

    async def _save_messages(
        self,
        conversation: Conversation,
        user_text: str,
        bot_text: str,
        tokens: int,
        whatsapp_msg_id: str,
    ) -> None:
        """Persiste mensagem do usuário e resposta do bot."""
        user_msg = Message(
            conversation_id=conversation.id,
            direction=MessageDirection.INBOUND,
            message_type=MessageType.TEXT,
            content=user_text,
            whatsapp_message_id=whatsapp_msg_id,
            is_ai_generated=False,
        )
        bot_msg = Message(
            conversation_id=conversation.id,
            direction=MessageDirection.OUTBOUND,
            message_type=MessageType.TEXT,
            content=bot_text,
            is_ai_generated=True,
            tokens_used=tokens,
        )
        self._db.add(user_msg)
        self._db.add(bot_msg)
        await self._db.flush()

    async def _update_conversation_state(
        self, conversation: Conversation, new_state: ConversationState
    ) -> None:
        conversation.state = new_state

        if new_state == ConversationState.CLOSED:
            conversation.status = ConversationStatus.CLOSED

        await self._db.flush()
