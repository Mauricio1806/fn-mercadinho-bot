"""
Checkpoint de qualidade — valida e sanitiza a resposta do Claude antes de enviá-la
ao cliente.
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

_ORDER_STATES = {
    ConversationState.ORDER_ITEMS,
    ConversationState.ORDER_CONFIRM,
    ConversationState.ORDER_DELIVERY,
    ConversationState.ORDER_PAYMENT,
}

_PRICE_RE = re.compile(r"R\$\s*(\d{1,4}(?:[.,]\d{2})?)")
_BLOCK_IN_TEXT_RE = re.compile(r"\bbloco\s+([A-Za-z][0-9]?)\b", re.IGNORECASE)

# Detecta qualquer string EMV (codigo Pix copia-e-cola)
_EMV_RE = re.compile(r"0002\d{2,4}26\d{2,4}0014br\.gov\.bcb\.pix[^\s]{20,}", re.IGNORECASE)
# Detecta strings longas que parecem EMV mesmo malformadas
_EMV_LOOSE_RE = re.compile(r"00020126[A-Za-z0-9]{30,}", re.IGNORECASE)


@dataclass
class ValidationResult:
    safe_response: str
    issues: list[str] = field(default_factory=list)
    was_modified: bool = False


def validate_response(
    response: str,
    state: ConversationState,
    order_ctx: OrderContext,
    business: BusinessConfig,
) -> ValidationResult:
    issues: list[str] = []
    text = response

    text, pix_issues = _check_pix_guard(text, state, business, order_ctx)
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

def _check_pix_guard(
    text: str,
    state: ConversationState,
    business: BusinessConfig,
    order_ctx: OrderContext,
) -> tuple[str, list[str]]:
    """
    Remove qualquer codigo EMV gerado pelo Claude e substitui pelo bloco
    correto com os dados reais do Pix. Funciona para qualquer estado.
    """
    issues: list[str] = []

    emv_found = _EMV_RE.search(text) or _EMV_LOOSE_RE.search(text)
    if not emv_found:
        return text, issues

    issues.append("PIX: codigo EMV detectado e removido — substituido por chave textual")
    logger.warning("PIX GUARD: codigo EMV interceptado e substituido")

    # Remove o codigo EMV da resposta
    text = _EMV_RE.sub("", text)
    text = _EMV_LOOSE_RE.sub("", text)

    # Se nao tiver dados Pix configurados, so remove e avisa
    if not business.pix_configured:
        return text.strip(), issues

    # Monta o valor correto
    total = order_ctx.total or 0.0
    valor_str = f"R$ {total:.2f}" if total > 0 else "R$ [VALOR DO PEDIDO]"

    bloco_pix = (
        f"Pague via Pix 💰\n"
        f"Chave {business.pix_tipo_chave.upper()}: {business.pix_chave}\n"
        f"Titular: {business.pix_titular} ({business.pix_banco})\n"
        f"Valor: {valor_str}\n\n"
        f"Apos pagar, manda o comprovante aqui pra gente confirmar!"
    )

    # Substitui qualquer referencia a "codigo" ou "aqui esta" que introduzia o EMV
    text = re.sub(
        r"(aqui est[aá] o c[oó]digo pix[^:]*:?|copia esse c[oó]digo[^:]*:?)\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Injeta o bloco correto se nao estiver na resposta ainda
    if business.pix_chave not in text:
        text = text.strip() + "\n\n" + bloco_pix

    return text.strip(), issues


# ── Verificação 2: coerência de estado ────────────────────────────────────────

def _check_state_coherence(text: str, state: ConversationState) -> list[str]:
    issues: list[str] = []

    if state == ConversationState.GREETING:
        payment_terms = re.compile(r"\bpix\b|\bpagar\b|\btotal\b|\bpedido\b|\bpagamento\b", re.I)
        if payment_terms.search(text):
            issues.append("ESTADO: resposta de GREETING contém termos de pedido/pagamento")

    if state not in _ORDER_STATES and re.search(r"R\$\s*\d", text):
        if state not in (ConversationState.MAIN_MENU, ConversationState.FREE_CHAT):
            issues.append(f"ESTADO: preço mencionado no estado inesperado={state.value}")

    return issues


# ── Verificação 3: sanity check de preços ─────────────────────────────────────

def _check_price_sanity(
    text: str,
    state: ConversationState,
    business: BusinessConfig,
) -> list[str]:
    issues: list[str] = []

    if state not in _ORDER_STATES:
        return issues

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
    price_ceiling = max_single * 20

    for match in _PRICE_RE.finditer(text):
        raw = match.group(1).replace(",", ".")
        try:
            price = float(raw)
        except ValueError:
            continue

        if price > price_ceiling:
            issues.append(f"PREÇO: valor R$ {price:.2f} parece alto (teto ×20 = R$ {price_ceiling:.2f})")
        elif 0 < price < 0.50:
            issues.append(f"PREÇO: valor R$ {price:.2f} suspeito — muito baixo")

    return issues


# ── Verificação 4: blocos de entrega ──────────────────────────────────────────

def _check_delivery_blocks(
    text: str,
    state: ConversationState,
    business: BusinessConfig,
) -> list[str]:
    issues: list[str] = []

    if state not in (ConversationState.ORDER_DELIVERY, ConversationState.ORDER_CONFIRM):
        return issues

    allowed = [b.upper() for b in business.delivery_blocos]
    if not allowed:
        return issues

    for match in _BLOCK_IN_TEXT_RE.finditer(text):
        block = match.group(1).upper()
        result = validate_delivery(block, "0", business)
        if not result.is_valid:
            issues.append(f"ENTREGA: resposta menciona bloco '{block}' fora da área de entrega")

    return issues
