"""Handlers de cada estado — decidem próximo estado baseado na resposta do Claude."""

from __future__ import annotations

import logging
import re

from app.models.conversation import ConversationState

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 20

# Heuristicas
_ORDER_INTENT_USER = ["1", "fazer pedido", "fazer um pedido", "quero pedir", "pedir", "comprar", "quero comprar"]
_DELIVERY_INTENT_USER = ["2", "entrega", "delivery", "taxa", "como entrega"]
_HOURS_INTENT_USER = ["3", "horário", "horario", "que horas", "abre", "fecha", "funciona"]
_OTHER_INTENT_USER = ["4", "duvida", "dúvida", "outra"]
_CONFIRM_USER = ["sim", "confirma", "confirmar", "isso", "isso mesmo", "só isso", "so isso", "ok", "pode", "fechar", "fecha", "pode fechar"]
_PICKUP_USER = ["balcão", "balcao", "retirar", "retirada", "buscar", "pegar", "vou la", "vou lá"]
_DELIVERY_PICK_USER = ["delivery", "entrega", "entregar", "entregue"]
_CANCEL_USER = ["cancela", "cancelar", "não quero", "nao quero", "desisti", "desisto"]


def _claude_summarizing_order(resp_lower: str) -> bool:
    """Detecta se Claude esta resumindo pedido (Total + valor)."""
    has_total = "total" in resp_lower and "r$" in resp_lower
    return has_total


def _claude_sent_pix(resp_lower: str) -> bool:
    """Detecta se Claude enviou dados de Pix."""
    return ("pix" in resp_lower or "chave" in resp_lower) and "r$" in resp_lower


def _claude_asked_delivery(resp_lower: str) -> bool:
    """Detecta se Claude perguntou sobre entrega/retirada."""
    return any(k in resp_lower for k in [
        "balcão", "balcao", "delivery", "retirar", "retirada", "entrega", "entregar"
    ])


def _claude_asked_address(resp_lower: str) -> bool:
    """Claude perguntou bloco/apartamento."""
    return any(k in resp_lower for k in ["bloco", "apartamento", "apto", "qual seu endereço", "endereco"])


def _claude_listed_products(resp_lower: str) -> bool:
    """Claude listou produtos com R$."""
    return resp_lower.count("r$") >= 2


def next_state_from_response(
    current_state: ConversationState,
    ai_response: str,
    user_message: str,
) -> ConversationState:
    resp_lower = (ai_response or "").lower()
    user_lower = (user_message or "").lower().strip()

    # Cancelamento global em qualquer estado de pedido
    if any(k in user_lower for k in _CANCEL_USER) and current_state in (
        ConversationState.ORDER_ITEMS,
        ConversationState.ORDER_CONFIRM,
        ConversationState.ORDER_DELIVERY,
    ):
        return ConversationState.MAIN_MENU

    match current_state:
        case ConversationState.GREETING:
            # Se ja escolheu opcao no primeiro turno, pula direto
            if any(k in user_lower for k in _ORDER_INTENT_USER):
                return ConversationState.ORDER_ITEMS
            if any(k in user_lower for k in _DELIVERY_INTENT_USER):
                return ConversationState.DELIVERY_INFO
            if any(k in user_lower for k in _HOURS_INTENT_USER):
                return ConversationState.HOURS_INFO
            return ConversationState.MAIN_MENU

        case ConversationState.MAIN_MENU:
            # Usuario escolheu opcao do menu (1/2/3/4 ou texto equivalente)
            if any(k in user_lower for k in _ORDER_INTENT_USER):
                return ConversationState.ORDER_ITEMS
            if any(k in user_lower for k in _DELIVERY_INTENT_USER):
                return ConversationState.DELIVERY_INFO
            if any(k in user_lower for k in _HOURS_INTENT_USER):
                return ConversationState.HOURS_INFO
            # Usuario disse nome de produto direto?
            if _claude_listed_products(resp_lower):
                return ConversationState.ORDER_ITEMS
            return ConversationState.MAIN_MENU

        case ConversationState.ORDER_ITEMS:
            # Claude resumiu pedido (Total: R$ X) -> confirma
            if _claude_summarizing_order(resp_lower) and _claude_asked_delivery(resp_lower):
                return ConversationState.ORDER_DELIVERY
            if _claude_summarizing_order(resp_lower):
                return ConversationState.ORDER_CONFIRM
            return ConversationState.ORDER_ITEMS

        case ConversationState.ORDER_CONFIRM:
            # Usuario confirmou
            if any(k in user_lower for k in _CONFIRM_USER):
                # Claude perguntou entrega -> vai pra delivery
                if _claude_asked_delivery(resp_lower):
                    return ConversationState.ORDER_DELIVERY
                # Claude ja mandou Pix -> payment
                if _claude_sent_pix(resp_lower):
                    return ConversationState.ORDER_PAYMENT
                # Default: pergunta sobre entrega
                return ConversationState.ORDER_DELIVERY
            return ConversationState.ORDER_CONFIRM

        case ConversationState.ORDER_DELIVERY:
            # Usuario escolheu retirada/delivery
            if any(k in user_lower for k in _PICKUP_USER):
                return ConversationState.ORDER_PAYMENT
            if any(k in user_lower for k in _DELIVERY_PICK_USER):
                # Se Claude pediu endereco, continua aqui
                if _claude_asked_address(resp_lower):
                    return ConversationState.ORDER_DELIVERY
                # Claude ja mandou Pix
                if _claude_sent_pix(resp_lower):
                    return ConversationState.ORDER_PAYMENT
                return ConversationState.ORDER_DELIVERY
            # Cliente mandou endereco (bloco/apto) e Claude mandou Pix
            if _claude_sent_pix(resp_lower):
                return ConversationState.ORDER_PAYMENT
            return ConversationState.ORDER_DELIVERY

        case ConversationState.ORDER_PAYMENT:
            return ConversationState.PAYMENT_RECEIPT

        case ConversationState.PAYMENT_RECEIPT:
            if any(k in user_lower for k in ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "menu"]):
                return ConversationState.GREETING
            return ConversationState.PAYMENT_RECEIPT

        case ConversationState.DELIVERY_INFO:
            if any(k in user_lower for k in _ORDER_INTENT_USER + ["sim"]):
                return ConversationState.ORDER_ITEMS
            return ConversationState.MAIN_MENU

        case ConversationState.HOURS_INFO:
            if any(k in user_lower for k in _ORDER_INTENT_USER):
                return ConversationState.ORDER_ITEMS
            return ConversationState.MAIN_MENU

        case ConversationState.FREE_CHAT:
            if any(k in user_lower for k in _ORDER_INTENT_USER):
                return ConversationState.ORDER_ITEMS
            return ConversationState.FREE_CHAT

        case ConversationState.CLOSED:
            return ConversationState.GREETING

    return current_state


def trim_history(history: list[dict[str, str]]) -> list[dict[str, str]]:
    if len(history) > MAX_HISTORY_MESSAGES:
        trimmed = history[-MAX_HISTORY_MESSAGES:]
        if trimmed and trimmed[0]["role"] != "user":
            trimmed = trimmed[1:]
        return trimmed
    return history


def extract_order_total(ai_response: str) -> float | None:
    patterns = [
        r"total[:\s]*r\$\s*([\d]+[.,][\d]{1,2})",
        r"r\$\s*([\d]+[.,][\d]{1,2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, ai_response.lower())
        if match:
            value_str = match.group(1).replace(",", ".")
            try:
                return float(value_str)
            except ValueError:
                pass
    return None
