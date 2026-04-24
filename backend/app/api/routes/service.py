"""
Rotas de serviço — usadas por integrações externas (n8n, automações).
Autenticação via header X-Service-Key (não JWT).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.session import get_db
from app.models.product import Product

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


# ── Auth ──────────────────────────────────────────────────────────────────────

def verify_service_key(x_service_key: str = Header(..., alias="X-Service-Key")) -> None:
    """Verifica a API key de serviço no header X-Service-Key."""
    if x_service_key != settings.service_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key de serviço inválida",
        )


# ── Schemas ───────────────────────────────────────────────────────────────────

class StockUpdateItem(BaseModel):
    product_id: str
    stock_quantity: int


class BulkStockUpdate(BaseModel):
    items: list[StockUpdateItem]


class StockUpdateResult(BaseModel):
    updated: int
    not_found: list[str]


# ── Rotas ─────────────────────────────────────────────────────────────────────

@router.patch(
    "/products/{product_id}/stock",
    dependencies=[Depends(verify_service_key)],
    summary="Atualiza estoque de um produto (n8n / automação)",
)
async def update_product_stock(
    product_id: str,
    body: StockUpdateItem,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Atualiza o `stock_quantity` de um produto.
    Usado pelo n8n para sincronizar estoque em tempo real.
    """
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    product.stock_quantity = body.stock_quantity
    await db.commit()

    logger.info("Estoque atualizado: %s → %d unidades", product.name, body.stock_quantity)
    return {"product_id": product_id, "stock_quantity": body.stock_quantity}


@router.patch(
    "/products/stock/bulk",
    dependencies=[Depends(verify_service_key)],
    response_model=StockUpdateResult,
    summary="Atualiza estoque em lote (n8n / automação)",
)
async def bulk_update_stock(
    body: BulkStockUpdate,
    db: AsyncSession = Depends(get_db),
) -> StockUpdateResult:
    """
    Atualiza o estoque de múltiplos produtos em uma única chamada.
    Ideal para sync com planilha Google Sheets via n8n.

    Body:
        {"items": [{"product_id": "uuid", "stock_quantity": 10}, ...]}
    """
    ids = [item.product_id for item in body.items]
    result = await db.execute(select(Product).where(Product.id.in_(ids)))
    products = {str(p.id): p for p in result.scalars().all()}

    not_found: list[str] = []
    updated = 0

    for item in body.items:
        if item.product_id not in products:
            not_found.append(item.product_id)
            continue
        products[item.product_id].stock_quantity = item.stock_quantity
        updated += 1

    await db.commit()
    logger.info("Estoque bulk: %d atualizados, %d não encontrados", updated, len(not_found))

    return StockUpdateResult(updated=updated, not_found=not_found)


@router.get(
    "/products",
    dependencies=[Depends(verify_service_key)],
    summary="Lista produtos com ID para mapeamento (n8n)",
)
async def list_products_for_service(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """
    Lista todos os produtos com id, nome e estoque atual.
    Use para montar a planilha de mapeamento no n8n.
    """
    result = await db.execute(select(Product).order_by(Product.name))
    products = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "stock_quantity": p.stock_quantity,
            "is_available": p.is_available,
        }
        for p in products
    ]
