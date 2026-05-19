"""
Mensagens de atualização de status de pedido enviadas para o cliente via WhatsApp.

Disparadas automaticamente quando o admin muda o status de um pedido
no endpoint PATCH /api/orders/{id}/status.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.models.order import Order, OrderStatus

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Mensagens por status (chave = novo status)
STATUS_MESSAGES: dict[OrderStatus, str] = {
    OrderStatus.PREPARING: "📦 Seu pedido tá sendo preparado! Já já fica prontinho 🙂",
    OrderStatus.READY: "🎉 Seu pedido tá pronto! Pode vir buscar no balcão ou aguarde a entrega.",
    OrderStatus.DELIVERING: "🛵 Saiu pra entrega! Em minutos chega aí. Aguarda um pouquinho 😊",
    OrderStatus.DELIVERED: "✅ Pedido entregue! Obrigado pela preferência. Qualquer coisa é só chamar 😊",
    OrderStatus.CANCELLED: "😕 Seu pedido foi cancelado. Qualquer dúvida, pode chamar aqui que a gente resolve!",
}

# Transições que NÃO devem gerar notificação
SILENT_TRANSITIONS = {
    OrderStatus.PENDING,
    OrderStatus.PAYMENT_CONFIRMED,
}


def build_status_message(
    old_status: OrderStatus,
    new_status: OrderStatus,
    order: Order | None = None,
) -> str | None:
    """
    Constrói a mensagem de notificação para a transição de status.

    Returns:
        String da mensagem ou None se não deve notificar.
    """
    # Não notifica se status não mudou
    if old_status == new_status:
        return None

    # Não notifica para status silenciosos
    if new_status in SILENT_TRANSITIONS:
        return None

    base_message = STATUS_MESSAGES.get(new_status)
    if not base_message:
        return None

    # Personaliza com número do pedido se disponível
    if order and order.id:
        order_ref = str(order.id)[:8].upper()
        return f"*Pedido #{order_ref}*\n{base_message}"

    return base_message


async def send_status_notification(
    order: Order,
    customer_phone: str,
    old_status: OrderStatus,
    new_status: OrderStatus,
) -> None:
    """
    Envia notificação WhatsApp para o cliente sobre mudança de status.

    Chamado automaticamente pelo endpoint PATCH /api/orders/{id}/status.
    """
    message = build_status_message(old_status, new_status, order)
    if not message:
        logger.debug(
            "Sem notificação para transição %s → %s (pedido %s)",
            old_status, new_status, order.id,
        )
        return

    try:
        from app.core.whatsapp.client import get_whatsapp_client
        whatsapp = get_whatsapp_client()

        # Remove '+' do número do cliente
        phone = customer_phone.lstrip("+")
        success = await whatsapp.send_text(phone, message)

        if success:
            logger.info(
                "Notificação de status enviada: pedido=%s status=%s cliente=%s",
                str(order.id)[:8], new_status.value, phone,
            )
        else:
            logger.warning(
                "Falhou ao enviar notificação de status: pedido=%s",
                str(order.id)[:8],
            )
    except Exception:
        logger.exception(
            "Erro ao enviar notificação de status para pedido %s", order.id
        )
