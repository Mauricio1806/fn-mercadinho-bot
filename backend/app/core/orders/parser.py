"""Extrai itens de pedido da resposta do Claude."""

from __future__ import annotations

import re

from app.core.orders.context import OrderItemContext


def parse_items_from_claude(ai_response: str) -> list[OrderItemContext]:
    """
    Tenta extrair itens e preços do resumo do pedido gerado pelo Claude.

    Formato esperado:
        • Coca-Cola 2L x2 — R$ 20,00
        • Água 500ml x1 — R$ 3,00

    Retorna lista de OrderItemContext. Retorna [] se não encontrar nada.
    """
    items: list[OrderItemContext] = []

    # Padrão: linha começando com bullet "• Nome xN — R$ XX,XX"
    # Usa MULTILINE + âncora de início de linha para evitar capturar * do markdown
    pattern = re.compile(
        r"^\s*[•\-]\s*(.+?)\s+x(\d+)\s*[—\-–]\s*R\$\s*([\d]+[.,][\d]{2})",
        re.IGNORECASE | re.MULTILINE,
    )

    for match in pattern.finditer(ai_response):
        name = match.group(1).strip()
        qty = int(match.group(2))
        # Preço do ITEM (subtotal = qty × unit), então unit_price = subtotal / qty
        subtotal_str = match.group(3).replace(",", ".")
        try:
            subtotal = float(subtotal_str)
            unit_price = subtotal / qty if qty > 0 else subtotal
        except ValueError:
            continue

        items.append(OrderItemContext(name=name, qty=qty, unit_price=unit_price))

    return items


def parse_delivery_type(user_message: str) -> str:
    """Detecta se cliente quer delivery ou retirada."""
    text = user_message.lower()
    pickup_keywords = ["retirar", "retirada", "buscar", "pegar", "vou buscar", "vou lá"]
    if any(k in text for k in pickup_keywords):
        return "pickup"
    return "delivery"
