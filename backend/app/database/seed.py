"""Popula o banco de dados com catálogo e usuário admin."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import bcrypt
import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal
from app.models.admin_user import AdminUser
from app.models.product import Product, ProductCategory

logger = logging.getLogger(__name__)


def _load_catalog() -> list[dict]:
    config_dir = Path(__file__).parent
    catalog_full = config_dir / "catalog_full.yaml"
    if catalog_full.exists():
        logger.info("Usando catálogo completo: %s", catalog_full)
        with catalog_full.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data or []
    logger.warning("catalog_full.yaml não encontrado — seed de produtos ignorado.")
    return []


async def seed_admin(session: AsyncSession) -> None:
    result = await session.execute(select(AdminUser).where(AdminUser.email == "atende096@gmail.com"))
    if result.scalar_one_or_none():
        logger.info("Admin já existe — pulando.")
        return
    hashed = bcrypt.hashpw("Atende0102*".encode(), bcrypt.gensalt()).decode()
    admin = AdminUser(
        email="atende096@gmail.com",
        hashed_password=hashed,
        full_name="Admin FN Mercadinho",
        is_active=True,
        is_superuser=True,
    )
    session.add(admin)
    await session.commit()
    logger.info("Admin criado com sucesso.")


async def seed_catalog(session: AsyncSession) -> None:
    catalogo = _load_catalog()
    if not catalogo:
        return

    result = await session.execute(select(ProductCategory))
    if result.scalars().first():
        logger.info("Catálogo já populado — pulando.")
        return

    created_categories = 0
    created_products = 0

    for sort_idx, cat_data in enumerate(catalogo):
        cat_name = cat_data.get("categoria", "Sem categoria")
        category = ProductCategory(name=cat_name, sort_order=sort_idx)
        session.add(category)
        await session.flush()
        created_categories += 1

        for prod_idx, prod_data in enumerate(cat_data.get("produtos", [])):
            if prod_data.get("nome") in ("TODO", None, ""):
                continue
            product = Product(
                name=prod_data["nome"],
                price=float(prod_data.get("preco", 0)),
                category_id=category.id,
                sort_order=prod_idx,
                is_available=True,
            )
            session.add(product)
            created_products += 1

    await session.commit()
    logger.info("Seed: %d categorias, %d produtos.", created_categories, created_products)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    async with AsyncSessionLocal() as session:
        await seed_admin(session)
        await seed_catalog(session)


if __name__ == "__main__":
    asyncio.run(main())
