"""Popula o banco de dados com o catálogo de produtos."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_business_config, get_settings
from app.database.session import AsyncSessionLocal
from app.models.product import Product, ProductCategory

logger = logging.getLogger(__name__)


def _load_catalog() -> list[dict]:
    """
    Carrega catálogo de produtos.
    Prioridade: config/catalog_full.yaml (gerado por parse_estoque.py)
    Fallback: seção 'catalogo' do business.yaml (apenas categorias).
    """
    settings = get_settings()
    config_dir = Path(__file__).parent

    catalog_full = config_dir / "catalog_full.yaml"
    if catalog_full.exists():
        logger.info("Usando catálogo completo: %s", catalog_full)
        with catalog_full.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data or []

    # Fallback: business.yaml (só para categorias sem produtos reais)
    logger.warning(
        "catalog_full.yaml não encontrado — usando business.yaml (sem produtos reais). "
        "Execute: python backend/parse_estoque.py"
    )
    config = get_business_config()
    return [c for c in config.catalogo if c.get("produtos")]


async def seed_catalog(session: AsyncSession) -> None:
    """Cria categorias e produtos no banco de dados."""
    catalogo = _load_catalog()

    if not catalogo:
        logger.warning("Catálogo vazio — seed ignorado.")
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
