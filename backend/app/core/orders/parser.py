"""Extrai itens de pedido da resposta do Claude."""

from __future__ import annotations
import re
from app.core.orders.context import OrderItemContext


def parse_items_from_claude(ai_response: str) -> list[OrderItemContext]:
    items: list[OrderItemContext] = []
    seen: set[tuple[str, int]] = set()

    def add_item(name: str, qty: int, subtotal: float) -> None:
        name = name.strip().rstrip(":")
        if not name:
            return
        unit_price = subtotal / qty if qty > 0 else subtotal
        key = (name.lower(), qty)
        if key not in seen:
            seen.add(key)
            items.append(OrderItemContext(name=name, qty=qty, unit_price=unit_price))

    # Formato: • Nome x2 — R$ 20,00  |  - Nome x2 — R$ 20,00
    for m in re.finditer(
        r"^[ \t]*[•\-\*]\s*(.+?)\s+[xX](\d+)\s*[—\-–·:]\s*R\$\s*([\d]+[.,][\d]{2})",
        ai_response, re.IGNORECASE | re.MULTILINE
    ):
        try:
            add_item(m.group(1), int(m.group(2)), float(m.group(3).replace(",", ".")))
        except ValueError:
            pass

    # Formato: • Nome (x2) — R$ 20,00
    for m in re.finditer(
        r"^[ \t]*[•\-\*]\s*(.+?)\s+\([xX](\d+)\)\s*[—\-–·:]\s*R\$\s*([\d]+[.,][\d]{2})",
        ai_response, re.IGNORECASE | re.MULTILINE
    ):
        try:
            add_item(m.group(1), int(m.group(2)), float(m.group(3).replace(",", ".")))
        except ValueError:
            pass

    # Formato: 2x Nome — R$ 20,00
    for m in re.finditer(
        r"^[ \t]*(\d+)[xX]\s*(.+?)\s*[—\-–·:]\s*R\$\s*([\d]+[.,][\d]{2})",
        ai_response, re.IGNORECASE | re.MULTILINE
    ):
        try:
            add_item(m.group(2), int(m.group(1)), float(m.group(3).replace(",", ".")))
        except ValueError:
            pass

    # Formato sem quantidade: • Nome — R$ 10,00  (qty=1)
    for m in re.finditer(
        r"^[ \t]*[•\-\*]\s*(.+?)\s*[—\-–]\s*R\$\s*([\d]+[.,][\d]{2})",
        ai_response, re.IGNORECASE | re.MULTILINE
    ):
        name = m.group(1).strip()
        # Ignora se já tem xN no nome (capturado acima)
        if re.search(r'[xX]\d+', name):
            continue
        try:
            add_item(name, 1, float(m.group(2).replace(",", ".")))
        except ValueError:
            pass

    return items


def parse_delivery_type(user_message: str) -> str:
    text = user_message.lower()
    pickup_keywords = ["retirar", "retirada", "buscar", "pegar", "vou buscar", "vou lá", "vou la"]
    if any(k in text for k in pickup_keywords):
        return "pickup"
    return "delivery"
