"""Notifica os donos do mercadinho via WhatsApp."""

from __future__ import annotations

import logging
import os

from app.config import BusinessConfig, get_business_config
from app.core.whatsapp.client import WhatsAppClient, get_whatsapp_client
from app.models.order import Order

logger = logging.getLogger(__name__)

# URL pública de áudio de alerta (beep sonoro para notificação de venda)
# Pode ser sobrescrito via env var ALERT_AUDIO_URL
_DEFAULT_ALERT_AUDIO_URL = os.getenv(
    "ALERT_AUDIO_URL",
    "https://www.soundjay.com/buttons/sounds/beep-07.mp3",
)


def _format_items(order: Order) -> str:
    return "\n".join(
        f"  • {item.product_name} x{item.quantity} — R$ {item.subtotal:.2f}"
        for item in (order.items or [])
    )


def _format_delivery(order: Order) -> str:
    if order.delivery_building_block:
        return (
            f"\n📍 Entrega: Bloco {order.delivery_building_block}, "
            f"Apto {order.delivery_apartment}"
        )
    return "\n🛍️ Retirada no balcão"


async def notify_new_order(
    order: Order,
    customer_phone: str,
    customer_name: str | None,
    whatsapp: WhatsAppClient | None = None,
    business: BusinessConfig | None = None,
) -> None:
    """
    Notifica o dono #1 sobre novo pedido aguardando comprovante PIX.
    Dono #2 NÃO recebe esta notificação — só recebe venda confirmada.
    """
    if business is None:
        business = get_business_config()
    if whatsapp is None:
        whatsapp = get_whatsapp_client()

    nome = customer_name or customer_phone
    total = float(order.total_amount)
    is_high_value = total >= business.valor_alto
    alert = "🚨 *PEDIDO ALTO* " if is_high_value else ""

    msg = (
        f"{alert}🛒 *Novo pedido — aguardando PIX*\n\n"
        f"👤 {nome}\n"
        f"📞 +{customer_phone}\n"
        f"{_format_items(order)}\n"
        f"{_format_delivery(order)}\n"
        f"💰 Total: R$ {total:.2f}\n\n"
        f"⏳ Aguardando comprovante do cliente\n"
        f"🔖 Pedido #{str(order.id)[:8].upper()}"
    )

    dono_1 = business.whatsapp_dono_1
    if dono_1 and dono_1 != "TODO":
        phone = dono_1.lstrip("+")
        success = await whatsapp.send_text(phone, msg)
        if not success:
            logger.warning("Falhou ao notificar dono_1 sobre pedido %s", order.id)


async def notify_sale_confirmed(
    order: Order,
    customer_phone: str,
    customer_name: str | None,
    commission_amount: float,
    whatsapp: WhatsAppClient | None = None,
    business: BusinessConfig | None = None,
) -> None:
    """
    Notifica AMBOS os donos quando a venda é confirmada via comprovante PIX.
    Dono #1 recebe áudio de alerta + mensagem de confirmação.
    Dono #2 recebe apenas a mensagem de confirmação.
    """
    if business is None:
        business = get_business_config()
    if whatsapp is None:
        whatsapp = get_whatsapp_client()

    nome = customer_name or customer_phone
    total = float(order.total_amount)

    msg = (
        f"✅ *VENDA CONFIRMADA!* 🎉\n\n"
        f"👤 {nome}\n"
        f"📞 +{customer_phone}\n"
        f"{_format_items(order)}\n"
        f"{_format_delivery(order)}\n"
        f"💰 Total: R$ {total:.2f}\n"
        f"💵 Comissão: R$ {commission_amount:.2f}\n\n"
        f"📦 Pedido em separação!\n"
        f"🔖 Pedido #{str(order.id)[:8].upper()}"
    )

    dono_1 = business.whatsapp_dono_1
    if dono_1 and dono_1 != "TODO":
        phone_1 = dono_1.lstrip("+")
        # Envia áudio de alerta sonoro ANTES do texto
        await whatsapp.send_audio_url(phone_1, _DEFAULT_ALERT_AUDIO_URL)
        success = await whatsapp.send_text(phone_1, msg)
        if not success:
            logger.warning("Falhou ao notificar dono_1 sobre venda confirmada %s", order.id)

    dono_2 = business.whatsapp_dono_2
    if dono_2 and dono_2 != "TODO":
        phone_2 = dono_2.lstrip("+")
        success = await whatsapp.send_text(phone_2, msg)
        if not success:
            logger.warning("Falhou ao notificar dono_2 sobre venda confirmada %s", order.id)
