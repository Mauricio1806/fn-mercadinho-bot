"""Testes das rotas de produtos."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, ProductCategory


@pytest.fixture
async def categoria(db_session: AsyncSession) -> ProductCategory:
    cat = ProductCategory(name="Bebidas", sort_order=0)
    db_session.add(cat)
    await db_session.flush()
    return cat


@pytest.fixture
async def produto(db_session: AsyncSession, categoria: ProductCategory) -> Product:
    p = Product(name="Coca-Cola 2L", price=10.00, category_id=categoria.id)
    db_session.add(p)
    await db_session.flush()
    return p


class TestListProducts:
    async def test_lista_produtos_publico(self, client: AsyncClient, produto: Product):
        resp = await client.get("/api/products/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(p["name"] == "Coca-Cola 2L" for p in data)

    async def test_lista_categorias_publico(self, client: AsyncClient, produto: Product):
        resp = await client.get("/api/products/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["name"] == "Bebidas"


class TestCreateProduct:
    async def test_cria_produto_com_auth(
        self, client: AsyncClient, categoria: ProductCategory, admin_token: str
    ):
        resp = await client.post(
            "/api/products/",
            json={
                "name": "Água 500ml",
                "price": 3.00,
                "category_id": str(categoria.id),
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Água 500ml"

    async def test_cria_produto_sem_auth(
        self, client: AsyncClient, categoria: ProductCategory
    ):
        resp = await client.post(
            "/api/products/",
            json={"name": "Teste", "price": 1.00, "category_id": str(categoria.id)},
        )
        assert resp.status_code in (401, 403)

    async def test_preco_negativo_rejeitado(
        self, client: AsyncClient, categoria: ProductCategory, admin_token: str
    ):
        resp = await client.post(
            "/api/products/",
            json={"name": "Grátis?", "price": -5.00, "category_id": str(categoria.id)},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422
