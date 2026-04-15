"""Testes das rotas de pedidos."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product, ProductCategory


@pytest.fixture
async def setup_order(db_session: AsyncSession, admin_token: str) -> dict:
    import uuid as _uuid

    cat = ProductCategory(name="Bebidas", sort_order=0)
    db_session.add(cat)
    await db_session.flush()

    prod = Product(name="Coca-Cola 2L", price=10.00, category_id=cat.id)
    db_session.add(prod)
    await db_session.flush()

    unique_phone = f"+557190{_uuid.uuid4().hex[:7]}"
    customer = Customer(phone=unique_phone, name="Maria")
    db_session.add(customer)
    await db_session.flush()

    order = Order(
        customer_id=customer.id,
        total_amount=10.00,
        status=OrderStatus.PENDING,
    )
    db_session.add(order)
    await db_session.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=prod.id,
        product_name="Coca-Cola 2L",
        quantity=1,
        unit_price=10.00,
    )
    db_session.add(item)
    await db_session.flush()

    return {"order": order, "product": prod, "customer": customer}


class TestListOrders:
    async def test_lista_pedidos_com_auth(
        self, client: AsyncClient, setup_order: dict, admin_token: str
    ):
        resp = await client.get(
            "/api/orders/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    async def test_lista_pedidos_sem_auth(self, client: AsyncClient):
        resp = await client.get("/api/orders/")
        assert resp.status_code in (401, 403)

    async def test_filtra_por_status(
        self, client: AsyncClient, setup_order: dict, admin_token: str
    ):
        resp = await client.get(
            "/api/orders/?status_filter=pending",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        for order in resp.json():
            assert order["status"] == "pending"


class TestGetOrder:
    async def test_busca_pedido_existente(
        self, client: AsyncClient, setup_order: dict, admin_token: str
    ):
        order_id = str(setup_order["order"].id)
        resp = await client.get(
            f"/api/orders/{order_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["total_amount"] == 10.0

    async def test_busca_pedido_inexistente(
        self, client: AsyncClient, admin_token: str
    ):
        import uuid
        resp = await client.get(
            f"/api/orders/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404


class TestUpdateOrderStatus:
    async def test_atualiza_status(
        self, client: AsyncClient, setup_order: dict, admin_token: str
    ):
        order_id = str(setup_order["order"].id)
        resp = await client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": "confirmed"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

    async def test_status_invalido(
        self, client: AsyncClient, setup_order: dict, admin_token: str
    ):
        order_id = str(setup_order["order"].id)
        resp = await client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": "status-invalido"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422
