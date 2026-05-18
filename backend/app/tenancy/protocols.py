"""Contratos que cada tenant pode implementar ou usar via defaults."""
from __future__ import annotations
from typing import Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class CatalogProvider(Protocol):
    async def search(self, term: str, tenant_id: UUID) -> str:
        """Retorna string formatada com produtos encontrados."""
        ...


@runtime_checkable
class DeliveryCalculator(Protocol):
    def calculate_fee(self, delivery_type: str, address: str | None) -> float:
        """Retorna taxa de entrega em reais."""
        ...

    def validate_area(self, address: str) -> bool:
        """Retorna True se o endereço está na área de entrega."""
        ...


@runtime_checkable
class OrderHooks(Protocol):
    async def on_payment_confirmed(self, order_id: str, customer_phone: str) -> None:
        ...

    async def on_order_dispatched(self, order_id: str, customer_phone: str) -> None:
        ...


@runtime_checkable
class PersonaOverride(Protocol):
    def system_prompt_addendum(self, state: str) -> str:
        """Texto adicional ao system prompt para esse estado."""
        ...
