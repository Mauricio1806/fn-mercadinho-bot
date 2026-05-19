"""
Helper interno de banco de dados para integrações de estoque.

Centraliza a lógica de upsert de produtos para que Bling, Tiny,
CSV e webhook genérico usem o mesmo código.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.base import ProductData
from app.models.product import Product, ProductCategory

logger = logging.getLogger(__name__)


async def _get_or_create_category(
    tenant_id: uuid.UUID, category_name: str, db: AsyncSession
) -> ProductCategory:
    """Busca ou cria categoria para o tenant."""
    result = await db.execute(
        select(ProductCategory).where(
            ProductCategory.tenant_id == tenant_id,
            ProductCategory.name == category_name,
        )
    )
    cat = result.scalar_one_or_none()
    if cat:
        return cat

    cat = ProductCategory(tenant_id=tenant_id, name=category_name, sort_order=0, is_active=True)
    db.add(cat)
    await db.flush()
    return cat


async def upsert_product_from_data(
    tenant_id: uuid.UUID,
    data: ProductData,
    db: AsyncSession,
) -> bool:
    """
    Faz upsert de um produto pelo external_id.

    Returns:
        True se foi criado, False se foi atualizado.
    """
    # Busca por external_id + tenant_id
    result = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant_id,
            Product.external_id == data.external_id,
            Product.external_source == data.external_source,
        )
    )
    product = result.scalar_one_or_none()

    category = await _get_or_create_category(tenant_id, data.category_name, db)
    now = datetime.now(timezone.utc)

    if product is None:
        # Cria novo produto
        product = Product(
            tenant_id=tenant_id,
            name=data.name,
            price=data.price,
            category_id=category.id,
            is_available=data.is_available,
            stock_quantity=data.stock_quantity,
            description=data.description,
            external_id=data.external_id,
            external_source=data.external_source,
            last_synced_at=now,
        )
        db.add(product)
        await db.flush()
        logger.debug("Produto criado: %s (external_id=%s)", data.name, data.external_id)
        return True
    else:
        # Atualiza produto existente
        product.name = data.name
        product.price = data.price
        product.category_id = category.id
        product.is_available = data.is_available
        if data.stock_quantity is not None:
            product.stock_quantity = data.stock_quantity
        if data.description is not None:
            product.description = data.description
        product.last_synced_at = now
        await db.flush()
        logger.debug("Produto atualizado: %s (external_id=%s)", data.name, data.external_id)
        return False


async def mark_product_unavailable(
    tenant_id: uuid.UUID, external_id: str, db: AsyncSession
) -> None:
    """Marca produto como indisponível sem deletar."""
    result = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant_id,
            Product.external_id == external_id,
        )
    )
    product = result.scalar_one_or_none()
    if product:
        product.is_available = False
        await db.flush()
