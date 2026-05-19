"""Rotas de produtos e categorias — multi-tenant."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.middleware.auth import get_current_admin, get_current_tenant_admin
from app.api.middleware.tenant_scope import TenantScope, get_tenant_scope
from app.database.session import get_db
from app.models.admin_user import AdminUser
from app.models.product import Product, ProductCategory
from app.schemas.product import CategoryResponse, ProductCreate, ProductResponse, ProductUpdate

router = APIRouter()


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    scope: TenantScope = Depends(get_tenant_scope),
) -> list[ProductCategory]:
    """Retorna categorias com produtos filtradas por tenant."""
    query = (
        select(ProductCategory)
        .options(selectinload(ProductCategory.products))
        .where(ProductCategory.is_active == True)  # noqa: E712
        .order_by(ProductCategory.sort_order)
    )
    query = scope.apply_filter(query, ProductCategory)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/", response_model=list[ProductResponse])
async def list_products(
    available_only: bool = True,
    db: AsyncSession = Depends(get_db),
    scope: TenantScope = Depends(get_tenant_scope),
) -> list[Product]:
    """Lista produtos filtrados por tenant."""
    query = select(Product).order_by(Product.sort_order)
    query = scope.apply_filter(query, Product)
    if available_only:
        query = query.where(Product.is_available == True)  # noqa: E712

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    db: AsyncSession = Depends(get_db),
    scope: TenantScope = Depends(get_tenant_scope),
    _: AdminUser = Depends(get_current_tenant_admin),
) -> Product:
    """Cria produto vinculado ao tenant do usuário logado."""
    tenant_id = scope.effective_tenant_id()
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Superadmin deve especificar o tenant_id do produto.",
        )
    product = Product(tenant_id=tenant_id, **body.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: uuid.UUID,
    body: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    scope: TenantScope = Depends(get_tenant_scope),
    _: AdminUser = Depends(get_current_tenant_admin),
) -> Product:
    query = select(Product).where(Product.id == product_id)
    query = scope.apply_filter(query, Product)
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado.")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return product
