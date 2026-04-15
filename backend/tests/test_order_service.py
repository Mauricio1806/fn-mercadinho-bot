"""Testes do serviço de pedidos e do parser de itens."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.orders.context import OrderContext, OrderItemContext
from app.core.orders.parser import parse_delivery_type, parse_items_from_claude
from app.core.orders.service import OrderService
from app.models.customer import Customer
from app.models.order import OrderStatus
from app.models.product import Product, ProductCategory


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def customer(db_session: AsyncSession) -> Customer:
    import uuid as _uuid
    c = Customer(phone=f"+5571{_uuid.uuid4().hex[:9]}", name="Teste")
    db_session.add(c)
    await db_session.flush()
    return c


@pytest_asyncio.fixture
async def products(db_session: AsyncSession):
    cat = ProductCategory(name="Bebidas", sort_order=0)
    db_session.add(cat)
    await db_session.flush()

    p1 = Product(name="Coca-Cola 2L", price=10.00, category_id=cat.id)
    p2 = Product(name="Água 500ml", price=3.00, category_id=cat.id)
    db_session.add(p1)
    db_session.add(p2)
    await db_session.flush()
    return [p1, p2]


# ── Testes do OrderContext ────────────────────────────────────────────────────

class TestOrderContext:
    def test_serializa_e_deserializa(self):
        ctx = OrderContext(
            items=[OrderItemContext(name="Coca-Cola", qty=2, unit_price=10.0)],
            delivery_type="delivery",
            building_block="A",
            apartment="201",
            total=20.0,
        )
        json_str = ctx.to_json()
        restored = OrderContext.from_json(json_str)

        assert len(restored.items) == 1
        assert restored.items[0].name == "Coca-Cola"
        assert restored.building_block == "A"

    def test_from_json_none_retorna_vazio(self):
        ctx = OrderContext.from_json(None)
        assert ctx.items == []
        assert ctx.total == 0.0

    def test_from_json_invalido_retorna_vazio(self):
        ctx = OrderContext.from_json("{invalido}")
        assert ctx.items == []

    def test_recalculate_total(self):
        ctx = OrderContext(items=[
            OrderItemContext(name="Coca", qty=2, unit_price=10.0),
            OrderItemContext(name="Água", qty=3, unit_price=3.0),
        ])
        ctx.recalculate_total()
        assert ctx.total == 29.0

    def test_format_summary(self):
        ctx = OrderContext(items=[
            OrderItemContext(name="Coca-Cola 2L", qty=1, unit_price=10.0),
        ])
        summary = ctx.format_summary()
        assert "Coca-Cola" in summary
        assert "10" in summary

    def test_subtotal_item(self):
        item = OrderItemContext(name="Coca", qty=3, unit_price=10.0)
        assert item.subtotal == 30.0


# ── Testes do parser ──────────────────────────────────────────────────────────

class TestParseItemsFromClaude:
    def test_extrai_item_simples(self):
        resp = "• Coca-Cola 2L x2 — R$ 20,00"
        items = parse_items_from_claude(resp)
        assert len(items) == 1
        assert items[0].name == "Coca-Cola 2L"
        assert items[0].qty == 2
        assert items[0].unit_price == 10.0

    def test_extrai_multiplos_itens(self):
        resp = (
            "📦 Seu pedido:\n"
            "• Coca-Cola 2L x1 — R$ 10,00\n"
            "• Água 500ml x2 — R$ 6,00\n"
            "💰 Total: R$ 16,00"
        )
        items = parse_items_from_claude(resp)
        assert len(items) == 2
        assert items[0].name == "Coca-Cola 2L"
        assert items[1].name == "Água 500ml"

    def test_sem_itens_retorna_vazio(self):
        items = parse_items_from_claude("Olá! O que deseja pedir?")
        assert items == []

    def test_item_com_ponto_no_preco(self):
        items = parse_items_from_claude("• Biscoito x1 — R$ 3.50")
        assert len(items) == 1
        assert items[0].unit_price == 3.50


class TestParseDeliveryType:
    def test_detecta_retirada(self):
        assert parse_delivery_type("vou retirar lá") == "pickup"
        assert parse_delivery_type("vou buscar") == "pickup"

    def test_default_delivery(self):
        assert parse_delivery_type("quero entrega") == "delivery"
        assert parse_delivery_type("sim, pode trazer") == "delivery"


# ── Testes do OrderService ────────────────────────────────────────────────────

class TestOrderService:
    async def test_cria_pedido_com_produtos_existentes(
        self, db_session: AsyncSession, customer: Customer, products: list
    ):
        ctx = OrderContext(
            items=[
                OrderItemContext(name="Coca-Cola 2L", qty=2, unit_price=10.0),
                OrderItemContext(name="Água 500ml", qty=1, unit_price=3.0),
            ],
            delivery_type="delivery",
            building_block="A",
            apartment="201",
        )
        ctx.recalculate_total()

        service = OrderService(db_session)
        order = await service.create_from_context(customer, ctx)

        assert order.id is not None
        assert order.status == OrderStatus.PENDING
        assert float(order.total_amount) == 23.0
        assert order.delivery_building_block == "A"
        assert order.delivery_apartment == "201"

    async def test_cria_pedido_incrementa_total_cliente(
        self, db_session: AsyncSession, customer: Customer, products: list
    ):
        assert customer.total_orders == 0

        ctx = OrderContext(items=[OrderItemContext(name="Coca-Cola 2L", qty=1, unit_price=10.0)])
        ctx.recalculate_total()

        service = OrderService(db_session)
        await service.create_from_context(customer, ctx)

        assert customer.total_orders == 1

    async def test_pedido_vazio_levanta_erro(
        self, db_session: AsyncSession, customer: Customer
    ):
        ctx = OrderContext(items=[])
        service = OrderService(db_session)

        with pytest.raises(ValueError, match="sem itens"):
            await service.create_from_context(customer, ctx)

    async def test_busca_pedido_com_itens(
        self, db_session: AsyncSession, customer: Customer, products: list
    ):
        ctx = OrderContext(items=[OrderItemContext(name="Coca-Cola 2L", qty=1, unit_price=10.0)])
        ctx.recalculate_total()

        service = OrderService(db_session)
        order = await service.create_from_context(customer, ctx)

        fetched = await service.get_order_with_items(order.id)
        assert fetched is not None
        assert len(fetched.items) == 1

    async def test_produto_nao_encontrado_usa_preco_do_contexto(
        self, db_session: AsyncSession, customer: Customer
    ):
        ctx = OrderContext(
            items=[OrderItemContext(name="Produto Inexistente XYZ", qty=1, unit_price=99.0)]
        )
        ctx.recalculate_total()

        service = OrderService(db_session)
        order = await service.create_from_context(customer, ctx)

        assert float(order.total_amount) == 99.0
