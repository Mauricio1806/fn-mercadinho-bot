"""Testes dos models SQLAlchemy."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product, ProductCategory


@pytest_asyncio.fixture
async def category(db_session: AsyncSession) -> ProductCategory:
    cat = ProductCategory(name="Bebidas", sort_order=0)
    db_session.add(cat)
    await db_session.flush()
    return cat


@pytest_asyncio.fixture
async def product(db_session: AsyncSession, category: ProductCategory) -> Product:
    prod = Product(name="Coca-Cola 2L", price=10.00, category_id=category.id)
    db_session.add(prod)
    await db_session.flush()
    return prod


@pytest_asyncio.fixture
async def customer(db_session: AsyncSession) -> Customer:
    c = Customer(phone="+5571999990001", name="João Silva")
    db_session.add(c)
    await db_session.flush()
    return c


class TestCustomer:
    async def test_cria_cliente(self, db_session: AsyncSession):
        c = Customer(phone="+5571999990002")
        db_session.add(c)
        await db_session.flush()
        assert c.id is not None
        assert c.is_blocked is False
        assert c.total_orders == 0

    async def test_phone_unico(self, db_session: AsyncSession, customer: Customer):
        c2 = Customer(phone=customer.phone)
        db_session.add(c2)
        with pytest.raises(Exception):
            await db_session.flush()

    async def test_repr(self, customer: Customer):
        assert "+5571999990001" in repr(customer)


class TestProduct:
    async def test_cria_produto(self, product: Product):
        assert product.id is not None
        assert product.price == 10.00
        assert product.is_available is True

    async def test_in_stock_disponivel(self, product: Product):
        assert product.in_stock is True

    async def test_in_stock_sem_estoque(self, product: Product):
        product.stock_quantity = 0
        assert product.in_stock is False

    async def test_in_stock_indisponivel(self, product: Product):
        product.is_available = False
        assert product.in_stock is False

    async def test_repr(self, product: Product):
        assert "Coca-Cola" in repr(product)


class TestOrder:
    async def test_cria_pedido(self, db_session: AsyncSession, customer: Customer, product: Product):
        order = Order(
            customer_id=customer.id,
            total_amount=10.00,
            status=OrderStatus.PENDING,
        )
        db_session.add(order)
        await db_session.flush()
        assert order.id is not None
        assert order.status == OrderStatus.PENDING
        assert order.pix_notified is False

    async def test_item_subtotal(self, db_session: AsyncSession, customer: Customer, product: Product):
        order = Order(customer_id=customer.id, total_amount=20.00)
        db_session.add(order)
        await db_session.flush()

        item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            quantity=2,
            unit_price=10.00,
        )
        db_session.add(item)
        await db_session.flush()

        assert item.subtotal == 20.00

    async def test_status_enum(self):
        assert OrderStatus.PENDING == "pending"
        assert OrderStatus.DELIVERED == "delivered"
        assert OrderStatus.CANCELLED == "cancelled"
