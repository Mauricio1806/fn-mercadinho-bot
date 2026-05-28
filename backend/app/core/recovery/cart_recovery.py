"""Serviço de recuperação de carrinho abandonado."""
from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, ConversationState, ConversationStatus
from app.models.customer import Customer
from app.models.recovery import RecoveryAttempt, RecoveryStatus

logger = logging.getLogger(__name__)

ABANDONED_STATES = {
    ConversationState.ORDER_ITEMS,
    ConversationState.ORDER_CONFIRM,
    ConversationState.ORDER_DELIVERY,
    ConversationState.ORDER_PAYMENT,
}

DEFAULT_MSG_1 = (
    "Oi! 👋 Vi que você estava montando um pedido aqui.\n\n"
    "Ainda quer finalizar? É só me dizer que eu retomo de onde paramos! 🛒"
)

DEFAULT_MSG_2 = (
    "Passando pra lembrar que estamos abertos e com tudo fresquinho! 😊\n\n"
    "Que tal aproveitar e fazer seu pedido hoje? 🛍️"
)


async def find_abandoned_carts(
    db: AsyncSession,
    tenant_id: UUID,
    minutes_threshold: int = 15,
) -> list[Conversation]:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes_threshold)
    result = await db.execute(
        select(Conversation).where(
            Conversation.tenant_id == tenant_id,
            Conversation.status == ConversationStatus.ACTIVE,
            Conversation.state.in_([s.value for s in ABANDONED_STATES]),
            Conversation.updated_at < cutoff,
        )
    )
    return list(result.scalars().all())


async def already_attempted(
    db: AsyncSession,
    conversation_id: UUID,
    attempt_number: int,
) -> bool:
    result = await db.execute(
        select(RecoveryAttempt).where(
            RecoveryAttempt.conversation_id == conversation_id,
            RecoveryAttempt.attempt_number == attempt_number,
        )
    )
    return result.scalar_one_or_none() is not None


async def run_recovery(
    db: AsyncSession,
    tenant_id: UUID,
    whatsapp_client,
    tenant_config: dict,
) -> dict:
    if not tenant_config.get("recovery", {}).get("enabled", False):
        return {"sent": 0, "skipped": 0, "reminded": 0, "reason": "disabled"}

    recovery_cfg = tenant_config.get("recovery", {})
    minutes = int(recovery_cfg.get("minutes_threshold", 15))
    msg_1 = recovery_cfg.get("message_1", DEFAULT_MSG_1)
    msg_2 = recovery_cfg.get("message_2", DEFAULT_MSG_2)

    abandoned = await find_abandoned_carts(db, tenant_id, minutes)
    sent = skipped = reminded = 0

    for conv in abandoned:
        customer_result = await db.execute(
            select(Customer).where(Customer.id == conv.customer_id)
        )
        customer = customer_result.scalar_one_or_none()
        if not customer:
            continue

        if not await already_attempted(db, conv.id, attempt_number=1):
            try:
                await whatsapp_client.send_text(customer.phone, msg_1)
                db.add(RecoveryAttempt(
                    tenant_id=tenant_id,
                    conversation_id=conv.id,
                    customer_phone=customer.phone,
                    status=RecoveryStatus.SENT,
                    attempt_number=1,
                ))
                await db.flush()
                sent += 1
                logger.info("Recovery #1 enviado: %s (tenant=%s)", customer.phone, tenant_id)
            except Exception as e:
                logger.error("Erro recovery #1 %s: %s", customer.phone, e)
                skipped += 1
            continue

        attempt1_result = await db.execute(
            select(RecoveryAttempt).where(
                RecoveryAttempt.conversation_id == conv.id,
                RecoveryAttempt.attempt_number == 1,
                RecoveryAttempt.status == RecoveryStatus.SENT,
            )
        )
        attempt1 = attempt1_result.scalar_one_or_none()

        if attempt1 and not await already_attempted(db, conv.id, attempt_number=2):
            hours_since = (datetime.now(timezone.utc) - attempt1.created_at).total_seconds() / 3600
            if hours_since >= 23:
                try:
                    await whatsapp_client.send_text(customer.phone, msg_2)
                    db.add(RecoveryAttempt(
                        tenant_id=tenant_id,
                        conversation_id=conv.id,
                        customer_phone=customer.phone,
                        status=RecoveryStatus.REMINDED,
                        attempt_number=2,
                    ))
                    await db.flush()
                    reminded += 1
                    logger.info("Recovery #2 enviado: %s (tenant=%s)", customer.phone, tenant_id)
                except Exception as e:
                    logger.error("Erro recovery #2 %s: %s", customer.phone, e)
                    skipped += 1
        else:
            skipped += 1

    await db.commit()
    return {"sent": sent, "skipped": skipped, "reminded": reminded}


async def mark_recovered(db: AsyncSession, conversation_id: UUID) -> None:
    await db.execute(
        update(RecoveryAttempt)
        .where(
            RecoveryAttempt.conversation_id == conversation_id,
            RecoveryAttempt.status.in_([RecoveryStatus.SENT, RecoveryStatus.REMINDED]),
        )
        .values(status=RecoveryStatus.CONVERTED)
    )
    await db.commit()
