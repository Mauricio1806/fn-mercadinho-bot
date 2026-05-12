"""Extrai itens de pedido da resposta do Claude."""

from __future__ import annotations

import re

from app.core.orders.context import OrderItemContext


def parse_items_from_claude(ai_response: str) -> list[OrderItemContext]:
    """
    Extrai itens do resumo do pedido gerado pelo Claude.
    Suporta formatos:
        • Nome x2 — R$ 20,00
        1x Nome — R$ 20,00
        - Nome x2 — R$ 20,00
    """
    items: list[OrderItemContext] = []

    # Formato 1: bullet + nome + xN + preco
    p1 = re.compile(
        r"^\s*[•\-]\s*(.+?)\s+x(\d+)\s*[—\-–]\s*R\$\s*([\d]+[.,][\d]{2})",
        re.IGNORECASE | re.MULTILINE,
    )
    # Formato 2: Nx nome + preco (ex: "1x Coca-Cola — R$ 5,00")
    p2 = re.compile(
        r"^\s*(\d+)x\s*(.+?)\s*[—\-–]\s*R\$\s*([\d]+[.,][\d]{2})",
        re.IGNORECASE | re.MULTILINE,
    )

    seen = set()

    for match in p1.finditer(ai_response):
        name = match.group(1).strip()
        qty = int(match.group(2))
        subtotal_str = match.group(3).replace(",", ".")
        try:
            subtotal = float(subtotal_str)
            unit_price = subtotal / qty if qty > 0 else subtotal
        except ValueError:
            continue
        key = (name.lower(), qty)
        if key not in seen:
            seen.add(key)
            items.append(OrderItemContext(name=name, qty=qty, unit_price=unit_price))

    for match in p2.finditer(ai_response):
        qty = int(match.group(1))
        name = match.group(2).strip()
        subtotal_str = match.group(3).replace(",", ".")
        try:
            subtotal = float(subtotal_str)
            unit_price = subtotal / qty if qty > 0 else subtotal
        except ValueError:
            continue
        key = (name.lower(), qty)
        if key not in seen:
            seen.add(key)
            items.append(OrderItemContext(name=name, qty=qty, unit_price=unit_price))

    return items


def parse_delivery_type(user_message: str) -> str:
    """Detecta se cliente quer delivery ou retirada."""
    text = user_message.lower()
    pickup_keywords = ["retirar", "retirada", "buscar", "pegar", "vou buscar", "vou lá"]
    if any(k in text for k in pickup_keywords):
        return "pickup"
    return "delivery"
