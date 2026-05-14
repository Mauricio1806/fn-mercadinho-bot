"""Handlers de cada estado — decidem próximo estado baseado na resposta do Claude."""

from __future__ import annotations

import logging
import re

from app.models.conversation import ConversationState

logger = logging.getLogger(__name__)

# Número máximo de mensagens de histórico enviadas ao Claude
MAX_HISTORY_MESSAGES = 20


def next_state_from_response(
    current_state: ConversationState,
    ai_response: str,
    user_message: str,
) -> ConversationState:
    """
    Determina o próximo estado baseado na resposta do Claude e na mensagem do usuário.
    Claude não gerencia o estado diretamente — é a engine que controla as transições.
    """
    resp_lower = ai_response.lower()
    user_lower = user_message.lower()

    match current_state:
        case ConversationState.GREETING:
            return ConversationState.MAIN_MENU

        case ConversationState.MAIN_MENU:
            # Claude respondeu sobre pedido?
            order_phrases = [
                "o que deseja", "o que você quer", "me diga o que",
                "deseja pedir", "quer pedir", "o que gostaria", "vai querer",
            ]
            if any(k in resp_lower for k in order_phrases):
                return ConversationState.ORDER_ITEMS
            # Respondeu sobre delivery?
            if any(k in resp_lower for k in ["condomínio", "bloco", "taxa", "tempo estimado"]):
                return ConversationState.DELIVERY_INFO
            # Respondeu horário?
            if any(k in resp_lower for k in ["segunda", "domingo", "abre", "fecha", "funcionamos"]):
                return ConversationState.HOURS_INFO
            # Continua no menu
            return ConversationState.MAIN_MENU

        case ConversationState.ORDER_ITEMS:
            # Claude mostrou resumo com total?
            if "total:" in resp_lower or "r$ " in resp_lower:
                if "confirmar" in resp_lower or "confirma" in resp_lower:
                    return ConversationState.ORDER_CONFIRM
            # Cliente cancelou?
            if any(k in user_lower for k in ["cancela", "não quero", "desisti"]):
                return ConversationState.MAIN_MENU
            return ConversationState.ORDER_ITEMS

        case ConversationState.ORDER_CONFIRM:
            # Claude pediu dados de entrega?
            if "bloco" in resp_lower or "apartamento" in resp_lower or "apto" in resp_lower:
                return ConversationState.ORDER_DELIVERY
            # Claude enviou Pix (retirada ou já tem endereço)?
            if "pix" in resp_lower and ("chave" in resp_lower or "r$" in resp_lower):
                return ConversationState.ORDER_PAYMENT
            # Cliente cancelou?
            if any(k in user_lower for k in ["cancela", "não", "nao"]):
                return ConversationState.MAIN_MENU
            return ConversationState.ORDER_CONFIRM

        case ConversationState.ORDER_DELIVERY:
            # Claude confirmou e enviou para pagamento?
            if "pix" in resp_lower and ("chave" in resp_lower or "r$" in resp_lower):
                return ConversationState.ORDER_PAYMENT
            return ConversationState.ORDER_DELIVERY

        case ConversationState.ORDER_PAYMENT:
            # Bot enviou o PIX — aguarda o comprovante
            return ConversationState.PAYMENT_RECEIPT

        case ConversationState.PAYMENT_RECEIPT:
            # Se chegou texto saudacao/inicio, sai do estado de comprovante
            if any(k in user_lower for k in ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "menu", "pedir", "pedido", "quero"]):
                return ConversationState.GREETING
            # Senao mantem aguardando comprovante (imagem)
            return ConversationState.PAYMENT_RECEIPT

        case ConversationState.DELIVERY_INFO:
            if any(k in user_lower for k in ["pedir", "quero", "sim"]):
                return ConversationState.ORDER_ITEMS
            return ConversationState.MAIN_MENU

        case ConversationState.HOURS_INFO:
            if any(k in user_lower for k in ["pedir", "quero", "pedido"]):
                return ConversationState.ORDER_ITEMS
            return ConversationState.MAIN_MENU

        case ConversationState.FREE_CHAT:
            if any(k in user_lower for k in ["pedido", "pedir", "quero comprar"]):
                return ConversationState.ORDER_ITEMS
            return ConversationState.FREE_CHAT

        case ConversationState.CLOSED:
            return ConversationState.GREETING

    return current_state


def trim_history(history: list[dict[str, str]]) -> list[dict[str, str]]:
    """Mantém apenas as últimas N mensagens para controlar o tamanho do contexto."""
    if len(history) > MAX_HISTORY_MESSAGES:
        # Mantém sempre um número par (user+assistant) para não quebrar a alternância
        trimmed = history[-MAX_HISTORY_MESSAGES:]
        # Garante que começa com "user"
        if trimmed and trimmed[0]["role"] != "user":
            trimmed = trimmed[1:]
        return trimmed
    return history


def extract_order_total(ai_response: str) -> float | None:
    """Tenta extrair o valor total do pedido da resposta do Claude."""
    # Busca padrão "Total: R$ 25,50" ou "R$ 25.50"
    patterns = [
        r"total[:\s]*r\$\s*([\d]+[.,][\d]{2})",
        r"r\$\s*([\d]+[.,][\d]{2})",
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
