"""Gerencia o contexto do pedido em andamento (armazenado em conversation.context_json)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class OrderItemContext:
    """Item do pedido em andamento."""

    name: str
    qty: int
    unit_price: float
    product_id: str | None = None  # UUID como string

    @property
    def subtotal(self) -> float:
        return self.qty * self.unit_price


@dataclass
class OrderContext:
    """Contexto completo do pedido em andamento — serializado em conversation.context_json."""

    items: list[OrderItemContext] = field(default_factory=list)
    delivery_type: str = "delivery"         # "delivery" ou "pickup"
    building_block: str | None = None
    apartment: str | None = None
    total: float = 0.0
    order_id: str | None = None             # UUID do Order criado, após confirmação
    notes: str | None = None

    @property
    def item_count(self) -> int:
        return sum(item.qty for item in self.items)

    def recalculate_total(self) -> None:
        self.total = sum(item.subtotal for item in self.items)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, json_str: str | None) -> "OrderContext":
        if not json_str:
            return cls()
        try:
            data = json.loads(json_str)
            items = [OrderItemContext(**i) for i in data.get("items", [])]
            return cls(
                items=items,
                delivery_type=data.get("delivery_type", "delivery"),
                building_block=data.get("building_block"),
                apartment=data.get("apartment"),
                total=data.get("total", 0.0),
                order_id=data.get("order_id"),
                notes=data.get("notes"),
            )
        except (json.JSONDecodeError, TypeError, KeyError):
            return cls()

    def format_summary(self) -> str:
        """Retorna resumo formatado para exibir ao cliente."""
        if not self.items:
            return "Nenhum item no pedido."

        lines = ["📦 *Seu pedido:*"]
        for item in self.items:
            lines.append(f"  • {item.name} x{item.qty} — R$ {item.subtotal:.2f}".replace(".", ","))

        if self.delivery_type == "delivery" and self.building_block:
            lines.append(f"\n📍 Entrega: Bloco {self.building_block}, Apto {self.apartment}")

        self.recalculate_total()
        lines.append(f"\n💰 *Total: R$ {self.total:.2f}*".replace(".", ","))
        return "\n".join(lines)
