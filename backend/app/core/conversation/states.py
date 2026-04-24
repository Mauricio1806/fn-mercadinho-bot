"""Transições válidas da máquina de estados da conversa."""

from __future__ import annotations

from app.models.conversation import ConversationState

# Mapa de transições: estado atual → estados possíveis
TRANSITIONS: dict[ConversationState, list[ConversationState]] = {
    ConversationState.GREETING: [
        ConversationState.MAIN_MENU,
    ],
    ConversationState.MAIN_MENU: [
        ConversationState.ORDER_ITEMS,
        ConversationState.DELIVERY_INFO,
        ConversationState.HOURS_INFO,
        ConversationState.FREE_CHAT,
        ConversationState.MAIN_MENU,
    ],
    ConversationState.ORDER_ITEMS: [
        ConversationState.ORDER_ITEMS,     # Adicionando mais itens
        ConversationState.ORDER_CONFIRM,
        ConversationState.MAIN_MENU,       # Cliente cancelou
    ],
    ConversationState.ORDER_CONFIRM: [
        ConversationState.ORDER_DELIVERY,
        ConversationState.ORDER_PAYMENT,   # Retirada: pula delivery
        ConversationState.ORDER_ITEMS,     # Cliente quer mudar
        ConversationState.MAIN_MENU,       # Cancelou
    ],
    ConversationState.ORDER_DELIVERY: [
        ConversationState.ORDER_PAYMENT,
        ConversationState.ORDER_DELIVERY,  # Dados inválidos, pedir de novo
    ],
    ConversationState.ORDER_PAYMENT: [
        ConversationState.PAYMENT_RECEIPT,
        ConversationState.CLOSED,  # Fallback direto (ex: retirada sem comprovante)
    ],
    ConversationState.PAYMENT_RECEIPT: [
        ConversationState.PAYMENT_RECEIPT,  # Aguardando comprovante
        ConversationState.CLOSED,           # Comprovante validado
    ],
    ConversationState.DELIVERY_INFO: [
        ConversationState.ORDER_ITEMS,     # Quer fazer pedido
        ConversationState.MAIN_MENU,
    ],
    ConversationState.HOURS_INFO: [
        ConversationState.MAIN_MENU,
        ConversationState.ORDER_ITEMS,
    ],
    ConversationState.FREE_CHAT: [
        ConversationState.MAIN_MENU,
        ConversationState.ORDER_ITEMS,
        ConversationState.FREE_CHAT,
    ],
    ConversationState.CLOSED: [
        ConversationState.GREETING,        # Nova conversa
    ],
}


def is_valid_transition(
    from_state: ConversationState, to_state: ConversationState
) -> bool:
    """Verifica se a transição entre estados é válida."""
    return to_state in TRANSITIONS.get(from_state, [])


def classify_intent(text: str) -> str:
    """
    Classifica intenção do cliente a partir do texto.
    Retorna uma das chaves: 'order', 'delivery', 'hours', 'cancel', 'confirm', 'other'.
    Usado como hint para o engine — Claude faz a decisão final.
    """
    text_lower = text.lower().strip()

    # Cancelamento (verificar ANTES de pedido para não confundir "não quero")
    cancel_keywords = ["cancela", "cancelar", "desistir", "tchau", "sair", "não quero", "nao quero"]
    if any(k in text_lower for k in cancel_keywords):
        return "cancel"
    # "não" como resposta isolada também é cancelamento
    if text_lower in ("nao", "não", "n", "nope"):
        return "cancel"

    # Confirmação
    confirm_keywords = ["sim", "ok", "confirmo", "confirmar", "pode", "tá bom", "tudo bem"]
    if any(k in text_lower for k in confirm_keywords):
        return "confirm"

    # Pedido
    order_keywords = ["1", "pedir", "pedido", "quero", "comprar", "quanto", "tem"]
    if any(k in text_lower for k in order_keywords):
        return "order"

    # Delivery
    delivery_keywords = ["2", "delivery", "entrega", "entregar", "motoboy"]
    if any(k in text_lower for k in delivery_keywords):
        return "delivery"

    # Horário
    hours_keywords = ["3", "horário", "hora", "funcionamento", "fecha", "abre"]
    if any(k in text_lower for k in hours_keywords):
        return "hours"

    return "other"
