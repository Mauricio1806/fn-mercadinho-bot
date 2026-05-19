"""Rota de dashboard — métricas por tenant + consolidado para superadmin."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.middleware.auth import get_current_superadmin
from app.api.middleware.tenant_scope import TenantScope, get_tenant_scope
from app.database.session import get_db
from app.models.admin_user import AdminUser
from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.models.tenant import Tenant

router = APIRouter()

_CONFIRMED_STATUSES = [
    OrderStatus.PAYMENT_CONFIRMED,
    OrderStatus.PREPARING,
    OrderStatus.READY,
    OrderStatus.DELIVERING,
    OrderStatus.DELIVERED,
]


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    scope: TenantScope = Depends(get_tenant_scope),
) -> dict:
    """Retorna métricas para o dashboard do tenant (ou do tenant filtrado)."""
    today = date.today()
    week_ago = today - timedelta(days=7)

    def _tenant_filter(q, model):
        return scope.apply_filter(q, model)

    orders_today = await db.execute(
        _tenant_filter(
            select(func.count(Order.id)).where(
                func.date(Order.created_at) == today,
                Order.status != OrderStatus.CANCELLED,
            ),
            Order,
        )
    )
    sales_today = await db.execute(
        _tenant_filter(
            select(func.count(Order.id)).where(
                func.date(Order.created_at) == today,
                Order.status.in_(_CONFIRMED_STATUSES),
            ),
            Order,
        )
    )
    revenue_today = await db.execute(
        _tenant_filter(
            select(func.sum(Order.total_amount)).where(
                func.date(Order.created_at) == today,
                Order.status.in_(_CONFIRMED_STATUSES),
            ),
            Order,
        )
    )
    commission_today = await db.execute(
        _tenant_filter(
            select(func.sum(Order.commission_amount)).where(
                func.date(Order.created_at) == today,
                Order.status.in_(_CONFIRMED_STATUSES),
            ),
            Order,
        )
    )
    revenue_week = await db.execute(
        _tenant_filter(
            select(func.sum(Order.total_amount)).where(
                func.date(Order.created_at) >= week_ago,
                Order.status.in_(_CONFIRMED_STATUSES),
            ),
            Order,
        )
    )
    commission_week = await db.execute(
        _tenant_filter(
            select(func.sum(Order.commission_amount)).where(
                func.date(Order.created_at) >= week_ago,
                Order.status.in_(_CONFIRMED_STATUSES),
            ),
            Order,
        )
    )
    total_customers = await db.execute(
        _tenant_filter(select(func.count(Customer.id)), Customer)
    )
    pending_orders = await db.execute(
        _tenant_filter(
            select(func.count(Order.id)).where(
                Order.status.in_(
                    [OrderStatus.PENDING, OrderStatus.PAYMENT_CONFIRMED, OrderStatus.PREPARING]
                )
            ),
            Order,
        )
    )

    return {
        "orders_today": orders_today.scalar() or 0,
        "sales_today": sales_today.scalar() or 0,
        "revenue_today": float(revenue_today.scalar() or 0),
        "commission_today": float(commission_today.scalar() or 0),
        "revenue_week": float(revenue_week.scalar() or 0),
        "commission_week": float(commission_week.scalar() or 0),
        "total_customers": total_customers.scalar() or 0,
        "pending_orders": pending_orders.scalar() or 0,
    }


@router.get("/consolidated")
async def get_consolidated_stats(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_superadmin),
) -> dict:
    """Métricas consolidadas de TODOS os tenants — apenas superadmin."""
    today = date.today()
    week_ago = today - timedelta(days=7)

    total_tenants = await db.execute(
        select(func.count(Tenant.id)).where(Tenant.is_active == True)  # noqa: E712
    )
    revenue_today_all = await db.execute(
        select(func.sum(Order.total_amount)).where(
            func.date(Order.created_at) == today,
            Order.status.in_(_CONFIRMED_STATUSES),
        )
    )
    commission_today_all = await db.execute(
        select(func.sum(Order.commission_amount)).where(
            func.date(Order.created_at) == today,
            Order.status.in_(_CONFIRMED_STATUSES),
        )
    )
    revenue_week_all = await db.execute(
        select(func.sum(Order.total_amount)).where(
            func.date(Order.created_at) >= week_ago,
            Order.status.in_(_CONFIRMED_STATUSES),
        )
    )
    commission_week_all = await db.execute(
        select(func.sum(Order.commission_amount)).where(
            func.date(Order.created_at) >= week_ago,
            Order.status.in_(_CONFIRMED_STATUSES),
        )
    )
    total_orders_all = await db.execute(select(func.count(Order.id)))

    return {
        "total_tenants_active": total_tenants.scalar() or 0,
        "revenue_today_all": float(revenue_today_all.scalar() or 0),
        "commission_today_all": float(commission_today_all.scalar() or 0),
        "revenue_week_all": float(revenue_week_all.scalar() or 0),
        "commission_week_all": float(commission_week_all.scalar() or 0),
        "total_orders_platform": total_orders_all.scalar() or 0,
    }


@router.get("/sales")
async def get_confirmed_sales(
    db: AsyncSession = Depends(get_db),
    scope: TenantScope = Depends(get_tenant_scope),
    limit: int = 50,
) -> list[dict]:
    """Últimas vendas confirmadas — filtradas por tenant."""
    query = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.customer))
        .where(Order.status.in_(_CONFIRMED_STATUSES))
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    query = scope.apply_filter(query, Order)
    result = await db.execute(query)
    orders = list(result.scalars().all())

    return [
        {
            "id": str(o.id)[:8].upper(),
            "created_at": o.created_at.isoformat(),
            "customer": o.customer.name or o.customer.phone if o.customer else "—",
            "items": [
                {"nome": i.product_name, "qty": i.quantity, "subtotal": float(i.subtotal)}
                for i in (o.items or [])
            ],
            "total": float(o.total_amount),
            "delivery_fee": float(o.delivery_fee),
            "commission": float(o.commission_amount or 0),
            "status": o.status.value,
            "tenant_id": str(o.tenant_id),
        }
        for o in orders
    ]
