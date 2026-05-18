"""Implementações default dos protocolos — usadas por qualquer tenant sem override."""
from __future__ import annotations
import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DefaultCatalogProvider:
    """Busca produtos no PostgreSQL filtrando por tenant_id."""

    def __init__(self, db_factory) -> None:
        self._db_factory = db_factory

    async def search(self, term: str, tenant_id: UUID) -> str:
        try:
            from app.database.session import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("""
                        SELECT p.name, p.price, pc.name as category
                        FROM products p
                        JOIN product_categories pc ON p.category_id = pc.id
                        WHERE p.is_available = true
                          AND p.name ILIKE :q
                          AND p.tenant_id = :tid
                        ORDER BY p.name
                        LIMIT 15
                    """),
                    {"q": f"%{term}%", "tid": str(tenant_id)},
                )
                rows = result.fetchall()

            if not rows:
                return f"Nenhum produto encontrado para '{term}'."

            lines = [f"Produtos encontrados para '{term}':"]
            for row in rows:
                lines.append(f"- {row.name}: R$ {float(row.price):.2f} ({row.category})")
            return "\n".join(lines)

        except Exception as e:
            logger.error("Erro ao buscar produtos tenant=%s term=%s: %s", tenant_id, term, e)
            return f"Erro temporário ao buscar '{term}'. Tente novamente."


class DefaultDeliveryCalculator:
    """Taxa baseada no config do tenant: taxa_proxima / taxa_distante."""

    def __init__(self, config: dict) -> None:
        self._config = config

    def calculate_fee(self, delivery_type: str, address: str | None) -> float:
        if delivery_type == "pickup":
            return 0.0
        delivery_cfg = self._config.get("delivery", {})
        return float(delivery_cfg.get("taxa_proxima", 3.0))

    def validate_area(self, address: str) -> bool:
        return True  # validação geográfica opcional por tenant


class DefaultOrderHooks:
    async def on_payment_confirmed(self, order_id: str, customer_phone: str) -> None:
        logger.info("on_payment_confirmed order=%s customer=%s", order_id, customer_phone)

    async def on_order_dispatched(self, order_id: str, customer_phone: str) -> None:
        logger.info("on_order_dispatched order=%s customer=%s", order_id, customer_phone)
