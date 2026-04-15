"""Popula o banco de dados com o catálogo do business.yaml."""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_business_config
from app.database.session import AsyncSessionLocal
from app.models.product import Product, ProductCategory

logger = logging.getLogger(__name__)


async def seed_catalog(session: AsyncSession) -> None:
    """Cria categorias e produtos a partir do business.yaml."""
    config = get_business_config()
    catalogo = config.catalogo

    if not catalogo:
        logger.warning("Catálogo vazio no business.yaml — seed ignorado.")
        return

    created_categories = 0
    created_products = 0

    for sort_idx, cat_data in enumerate(catalogo):
        cat_name = cat_data.get("categoria", "Sem categoria")

        category = ProductCategory(
            name=cat_name,
            sort_order=sort_idx,
        )
        session.add(category)
        await session.flush()  # Garante o ID antes de criar produtos
        created_categories += 1

        for prod_idx, prod_data in enumerate(cat_data.get("produtos", [])):
            if prod_data.get("nome") == "TODO":
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
    logger.info(
        "Seed concluído: %d categorias, %d produtos.",
        created_categories,
        created_products,
    )


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    async with AsyncSessionLocal() as session:
        await seed_catalog(session)


if __name__ == "__main__":
    asyncio.run(main())
