"""Rota de dashboard — métricas e stats."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.middleware.auth import get_current_admin
from app.config import get_business_config
from app.database.session import get_db
from app.models.admin_user import AdminUser
from app.models.customer import Customer
from app.models.order import Order, OrderStatus

router = APIRouter()

# Status considerados como "venda efetivada" (PIX confirmado)
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
    _: AdminUser = Depends(get_current_admin),
) -> dict:
    """Retorna métricas para o dashboard."""
    today = date.today()
    week_ago = today - timedelta(days=7)
    business = get_business_config()

    # Pedidos hoje (exceto cancelados)
    orders_today = await db.execute(
        select(func.count(Order.id)).where(
            func.date(Order.created_at) == today,
            Order.status != OrderStatus.CANCELLED,
        )
    )

    # Vendas confirmadas hoje (PIX validado)
    sales_today = await db.execute(
        select(func.count(Order.id)).where(
            func.date(Order.created_at) == today,
            Order.status.in_(_CONFIRMED_STATUSES),
        )
    )

    # Receita confirmada hoje
    revenue_today = await db.execute(
        select(func.sum(Order.total_amount)).where(
            func.date(Order.created_at) == today,
            Order.status.in_(_CONFIRMED_STATUSES),
        )
    )

    # Comissão gerada hoje
    commission_today = await db.execute(
        select(func.sum(Order.commission_amount)).where(
            func.date(Order.created_at) == today,
            Order.status.in_(_CONFIRMED_STATUSES),
        )
    )

    # Receita confirmada da semana
    revenue_week = await db.execute(
        select(func.sum(Order.total_amount)).where(
            func.date(Order.created_at) >= week_ago,
            Order.status.in_(_CONFIRMED_STATUSES),
        )
    )

    # Comissão da semana
    commission_week = await db.execute(
        select(func.sum(Order.commission_amount)).where(
            func.date(Order.created_at) >= week_ago,
            Order.status.in_(_CONFIRMED_STATUSES),
        )
    )

    # Total de clientes
    total_customers = await db.execute(select(func.count(Customer.id)))

    # Pedidos aguardando separação
    pending_orders = await db.execute(
        select(func.count(Order.id)).where(
            Order.status.in_([OrderStatus.PENDING, OrderStatus.PAYMENT_CONFIRMED, OrderStatus.PREPARING])
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
        "commission_rate_pct": business.comissao_percentual,
    }


@router.get("/sales")
async def get_confirmed_sales(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
    limit: int = 50,
) -> list[dict]:
    """Retorna as últimas vendas confirmadas (PIX validado)."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.customer))
        .where(Order.status.in_(_CONFIRMED_STATUSES))
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
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
            "delivery": (
                f"Bloco {o.delivery_building_block}, Apto {o.delivery_apartment}"
                if o.delivery_building_block
                else "Retirada"
            ),
        }
        for o in orders
    ]
