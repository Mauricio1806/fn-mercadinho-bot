"""
Webhook genérico — aceita qualquer sistema que envie JSON.

Formato esperado do payload:
{
  "external_id": "SKU001",
  "name": "Produto X",          # ou "nome"
  "price": 9.99,                # ou "preco"
  "category": "Bebidas",        # ou "categoria"
  "available": true,            # ou "disponivel"
  "stock_quantity": 50          # opcional
}
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.integrations.base import InventorySync, ProductData, SyncResult

logger = logging.getLogger(__name__)


class GenericWebhookSync(InventorySync):
    """
    Webhook genérico para qualquer sistema de gestão.
    Aceita payload flexível em PT ou EN.
    """

    source_name = "webhook"

    def __init__(self, db=None) -> None:
        self._db = db

    def _parse_payload(self, payload: dict[str, Any]) -> ProductData:
        """Parseia payload flexível (suporta campos em PT e EN)."""
        external_id = str(
            payload.get("external_id") or payload.get("id") or payload.get("sku") or ""
        )
        if not external_id:
            raise ValueError("Payload deve ter 'external_id', 'id' ou 'sku'")

        name = (
            payload.get("name")
            or payload.get("nome")
            or payload.get("descricao")
            or ""
        )
        if not name:
            raise ValueError("Payload deve ter 'name' ou 'nome'")

        price_raw = payload.get("price") or payload.get("preco") or 0
        try:
            price = float(str(price_raw).replace(",", "."))
        except (ValueError, TypeError):
            price = 0.0

        category = (
            payload.get("category")
            or payload.get("categoria")
            or "Geral"
        )

        available_raw = payload.get("available", payload.get("disponivel", True))
        if isinstance(available_raw, bool):
            is_available = available_raw
        else:
            is_available = str(available_raw).lower() in ("true", "sim", "1", "yes")

        stock_raw = payload.get("stock_quantity") or payload.get("estoque")
        stock = None
        if stock_raw is not None:
            try:
                stock = int(stock_raw)
                # Se estoque zerado, marca indisponível
                if stock <= 0:
                    is_available = False
            except (ValueError, TypeError):
                pass

        return ProductData(
            name=str(name),
            price=price,
            category_name=str(category),
            external_id=external_id,
            external_source=self.source_name,
            is_available=is_available,
            stock_quantity=stock,
            description=payload.get("description") or payload.get("descricao"),
        )

    async def handle_webhook(self, tenant_id: uuid.UUID, payload: dict[str, Any]) -> SyncResult:
        """Processa evento genérico e faz upsert do produto."""
        result = SyncResult(success=True)

        try:
            product_data = self._parse_payload(payload)
        except ValueError as e:
            result.add_error(str(e))
            return result

        try:
            from app.integrations._db_helper import upsert_product_from_data
            created = await upsert_product_from_data(tenant_id, product_data, self._db)
            if created:
                result.created = 1
            else:
                result.updated = 1

            if self._db:
                await self._db.commit()
        except Exception as e:
            result.add_error(f"Upsert falhou: {e}")

        return result

    # Métodos ABC não implementados para webhook genérico
    async def sync_all(self, tenant_id: uuid.UUID) -> SyncResult:
        raise NotImplementedError("GenericWebhook não suporta sync_all — use os eventos individuais.")

    async def sync_product(self, tenant_id: uuid.UUID, external_id: str) -> ProductData | None:
        raise NotImplementedError("GenericWebhook não suporta sync_product.")

    async def validate_credentials(self, config: dict[str, Any]) -> bool:
        return True  # Webhook genérico não precisa de credenciais
