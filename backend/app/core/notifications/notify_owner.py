"""Notifica os donos do mercadinho via WhatsApp."""

from __future__ import annotations

import logging

from app.config import BusinessConfig, get_business_config
from app.core.whatsapp.client import WhatsAppClient, get_whatsapp_client
from app.models.order import Order

logger = logging.getLogger(__name__)


async def notify_new_order(
    order: Order,
    customer_phone: str,
    customer_name: str | None,
    whatsapp: WhatsAppClient | None = None,
    business: BusinessConfig | None = None,
) -> None:
    """
    Envia notificação de novo pedido para os donos.
    Falha silenciosa — não interrompe o fluxo se não conseguir notificar.
    """
    if business is None:
        business = get_business_config()
    if whatsapp is None:
        whatsapp = get_whatsapp_client()

    nome = customer_name or customer_phone
    total = float(order.total_amount)

    items_text = "\n".join(
        f"  • {item.product_name} x{item.quantity} — R$ {item.subtotal:.2f}"
        for item in (order.items or [])
    )
    delivery_text = ""
    if order.delivery_building_block:
        delivery_text = (
            f"\n📍 Entrega: Bloco {order.delivery_building_block}, "
            f"Apto {order.delivery_apartment}"
        )

    is_high_value = total >= business.valor_alto
    alert = "🚨 *PEDIDO ALTO* " if is_high_value else ""

    msg = (
        f"{alert}🛒 *Novo pedido!*\n\n"
        f"👤 Cliente: {nome}\n"
        f"📞 Telefone: +{customer_phone}\n"
        f"{items_text}\n"
        f"💰 Total: R$ {total:.2f}"
        f"{delivery_text}\n\n"
        f"🕐 Pedido #{str(order.id)[:8].upper()}"
    )

    owners = [
        business.whatsapp_dono_1,
        business.whatsapp_dono_2,
    ]

    for owner in owners:
        if owner and owner != "TODO":
            phone = owner.lstrip("+")
            success = await whatsapp.send_text(phone, msg)
            if not success:
                logger.warning("Falhou ao notificar dono %s sobre pedido %s", owner, order.id)
