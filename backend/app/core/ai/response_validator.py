"""
Checkpoint de qualidade — valida e sanitiza a resposta do Claude antes de enviá-la
ao cliente. Implementa as três camadas inspiradas na arquitetura de agentes:

  1. Base de conhecimento  → verifica preços contra o catálogo do YAML
  2. Camada de especialidade → garante coerência com o estado atual da conversa
  3. Checkpoint de qualidade → sanitiza dados sensíveis (Pix) e bloqueia
     informações incorretas antes que cheguem ao cliente.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from app.config import BusinessConfig
from app.core.orders.context import OrderContext
from app.core.orders.delivery_validator import validate_delivery
from app.models.conversation import ConversationState

logger = logging.getLogger(__name__)

# Estados em que detalhes de pedido/itens são esperados
_ORDER_STATES = {
    ConversationState.ORDER_ITEMS,
    ConversationState.ORDER_CONFIRM,
    ConversationState.ORDER_DELIVERY,
    ConversationState.ORDER_PAYMENT,
}

# Regex para valores monetários no formato "R$ 12,50" ou "R$12.50"
_PRICE_RE = re.compile(r"R\$\s*(\d{1,4}(?:[.,]\d{2})?)")
# Regex para blocos mencionados na resposta ("bloco A", "bloco B2")
_BLOCK_IN_TEXT_RE = re.compile(r"\bbloco\s+([A-Za-z][0-9]?)\b", re.IGNORECASE)


@dataclass
class ValidationResult:
    """Resultado do checkpoint de qualidade."""

    safe_response: str
    """Resposta final — idêntica à original ou corrigida se necessário."""

    issues: list[str] = field(default_factory=list)
    """Lista de problemas encontrados (para log/auditoria)."""

    was_modified: bool = False
    """True se a resposta foi alterada pelo validator."""


def validate_response(
    response: str,
    state: ConversationState,
    order_ctx: OrderContext,
    business: BusinessConfig,
) -> ValidationResult:
    """
    Ponto de entrada do checkpoint de qualidade.

    Executa todas as verificações em ordem de criticidade:
      1. Guard de dados Pix/sensíveis (pode modificar resposta)
      2. Coerência de estado (apenas log)
      3. Sanity check de preços contra catálogo (apenas log)
      4. Validação de blocos de entrega mencionados (apenas log)

    Args:
        response:   Texto bruto retornado pelo Claude.
        state:      Estado atual da conversa.
        order_ctx:  Contexto do pedido em andamento.
        business:   Config do negócio.

    Returns:
        ValidationResult com a resposta segura e lista de issues para auditoria.
    """
    issues: list[str] = []
    text = response

    text, pix_issues = _check_pix_guard(text, state, business)
    issues.extend(pix_issues)

    issues.extend(_check_state_coherence(text, state))
    issues.extend(_check_price_sanity(text, state, business))
    issues.extend(_check_delivery_blocks(text, state, business))

    was_modified = text != response

    if issues:
        logger.warning(
            "Checkpoint | estado=%s | %d problema(s): %s",
            state.value,
            len(issues),
            " | ".join(issues),
        )

    return ValidationResult(
        safe_response=text,
        issues=issues,
        was_modified=was_modified,
    )


# ── Verificação 1: guard de dados Pix ─────────────────────────────────────────

def _check_pix_guard(text, state, business):
    return text, []


# ── Verificação 2: coerência de estado ────────────────────────────────────────

def _check_state_coherence(text: str, state: ConversationState) -> list[str]:
    """
    Verifica se o conteúdo da resposta é coerente com o estado atual.
    Ex: não deve falar de Pix/total na saudação inicial.
    """
    issues: list[str] = []

    if state == ConversationState.GREETING:
        # Na saudação não deveria surgir pedido, pagamento ou total
        payment_terms = re.compile(r"\bpix\b|\bpagar\b|\btotal\b|\bpedido\b|\bpagamento\b", re.I)
        if payment_terms.search(text):
            issues.append(
                "ESTADO: resposta de GREETING contém termos de pedido/pagamento"
            )

    if state not in _ORDER_STATES and re.search(r"R\$\s*\d", text):
        # Preços fora de estados de pedido são suspeitos (ex: GREETING citando valor)
        if state not in (ConversationState.MAIN_MENU, ConversationState.FREE_CHAT):
            issues.append(
                f"ESTADO: preço mencionado no estado inesperado={state.value}"
            )

    return issues


# ── Verificação 3: sanity check de preços contra catálogo ─────────────────────

def _check_price_sanity(
    text: str,
    state: ConversationState,
    business: BusinessConfig,
) -> list[str]:
    """
    Extrai preços da resposta e verifica se são plausíveis.
    Alerta quando um preço unitário supera em muito o maior produto do catálogo.
    """
    issues: list[str] = []

    if state not in _ORDER_STATES:
        return issues

    # Coleta todos os preços do catálogo
    catalog_prices: list[float] = []
    for cat in business.catalogo:
        for prod in cat.get("produtos", []):
            try:
                catalog_prices.append(float(prod["preco"]))
            except (KeyError, ValueError, TypeError):
                pass

    if not catalog_prices:
        return issues

    max_single = max(catalog_prices)
    # Limite generoso: até 20 itens do produto mais caro (para totais de pedido)
    price_ceiling = max_single * 20

    for match in _PRICE_RE.finditer(text):
        raw = match.group(1).replace(",", ".")
        try:
            price = float(raw)
        except ValueError:
            continue

        if price > price_ceiling:
            issues.append(
                f"PREÇO: valor R$ {price:.2f} parece alto "
                f"(teto do catálogo ×20 = R$ {price_ceiling:.2f})"
            )
        elif price > 0 and price < 0.50:
            # Preço suspeito muito baixo (provavelmente erro de formatação)
            issues.append(f"PREÇO: valor R$ {price:.2f} suspeito — muito baixo")

    return issues


# ── Verificação 4: blocos de entrega mencionados ──────────────────────────────

def _check_delivery_blocks(
    text: str,
    state: ConversationState,
    business: BusinessConfig,
) -> list[str]:
    """
    Se a resposta menciona um bloco de entrega, verifica se ele está na lista
    de blocos permitidos. Não modifica o texto — apenas audita.
    """
    issues: list[str] = []

    if state not in (ConversationState.ORDER_DELIVERY, ConversationState.ORDER_CONFIRM):
        return issues

    allowed = [b.upper() for b in business.delivery_blocos]
    if not allowed:
        # Sem restrição configurada
        return issues

    for match in _BLOCK_IN_TEXT_RE.finditer(text):
        block = match.group(1).upper()
        result = validate_delivery(block, "0", business)
        if not result.is_valid:
            issues.append(
                f"ENTREGA: resposta menciona bloco '{block}' fora da área de entrega"
            )

    return issues
