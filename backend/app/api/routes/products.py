"""Rotas de produtos e categorias."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.middleware.auth import get_current_admin
from app.database.session import get_db
from app.models.admin_user import AdminUser
from app.models.product import Product, ProductCategory
from app.schemas.product import CategoryResponse, ProductCreate, ProductResponse, ProductUpdate

router = APIRouter()


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
) -> list[ProductCategory]:
    """Retorna categorias com produtos — endpoint público (bot usa isso)."""
    result = await db.execute(
        select(ProductCategory)
        .options(selectinload(ProductCategory.products))
        .where(ProductCategory.is_active == True)  # noqa: E712
        .order_by(ProductCategory.sort_order)
    )
    return list(result.scalars().all())


@router.get("/", response_model=list[ProductResponse])
async def list_products(
    available_only: bool = True,
    db: AsyncSession = Depends(get_db),
) -> list[Product]:
    query = select(Product).order_by(Product.sort_order)
    if available_only:
        query = query.where(Product.is_available == True)  # noqa: E712

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> Product:
    product = Product(**body.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: uuid.UUID,
    body: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> Product:
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado.")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return product
