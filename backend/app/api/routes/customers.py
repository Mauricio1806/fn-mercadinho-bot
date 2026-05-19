"""Rotas de clientes — multi-tenant."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.tenant_scope import TenantScope, get_tenant_scope
from app.database.session import get_db
from app.models.customer import Customer
from app.schemas.customer import CustomerResponse, CustomerUpdate

router = APIRouter()


@router.get("/", response_model=list[CustomerResponse])
async def list_customers(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    scope: TenantScope = Depends(get_tenant_scope),
) -> list[Customer]:
    """Lista clientes filtrados por tenant."""
    query = select(Customer).order_by(Customer.created_at.desc()).limit(limit).offset(offset)
    query = scope.apply_filter(query, Customer)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    scope: TenantScope = Depends(get_tenant_scope),
) -> Customer:
    query = select(Customer).where(Customer.id == customer_id)
    query = scope.apply_filter(query, Customer)
    result = await db.execute(query)
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado."
        )
    return customer


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: uuid.UUID,
    body: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    scope: TenantScope = Depends(get_tenant_scope),
) -> Customer:
    query = select(Customer).where(Customer.id == customer_id)
    query = scope.apply_filter(query, Customer)
    result = await db.execute(query)
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado."
        )

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)

    await db.commit()
    await db.refresh(customer)
    return customer
