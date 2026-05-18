"""Módulo Pix — gera mensagem de pagamento formatada."""

from __future__ import annotations

from app.config import BusinessConfig, get_business_config


def build_pix_message(total: float, business: BusinessConfig | None = None) -> str:
    """
    Gera mensagem de cobrança via Pix pronta para enviar ao cliente.

    Args:
        total: Valor total do pedido.
        business: Configuração do negócio (opcional, usa singleton se não informado).

    Returns:
        Mensagem formatada para envio no WhatsApp.
    """
    if business is None:
        business = get_business_config()

    if not business.pix_configured:
        return (
            f"💰 *Total: R$ {total:.2f}*\n\n"
            "O pagamento pode ser feito no momento da entrega. "
            "Aceitamos dinheiro e Pix! 😊"
        )

    return (
        f"💰 *Pagar via Pix*\n\n"
        f"Chave ({business.pix_tipo_chave}): `{business.pix_chave}`\n"
        f"Titular: {business.pix_titular} — {business.pix_banco}\n"
        f"Valor: *R$ {total:.2f}*\n\n"
        "Após o pagamento, nos manda o comprovante 📸\n"
        "Seu pedido será separado assim que confirmarmos! ✅"
    )


def format_currency(value: float) -> str:
    """Formata valor monetário no padrão brasileiro."""
    return f"R$ {value:.2f}".replace(".", ",")
