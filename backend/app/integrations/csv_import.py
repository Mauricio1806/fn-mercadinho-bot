"""
Importação de catálogo via CSV.

Formato CSV esperado:
nome,preco,categoria,disponivel,external_id

Exemplo:
Coca-Cola 2L,9.99,Bebidas,true,SKU001
Biscoito Oreo,4.50,Biscoitos,true,SKU002
"""

from __future__ import annotations

import csv
import io
import logging
import uuid
from typing import Any

from app.integrations.base import InventorySync, ProductData, SyncResult

logger = logging.getLogger(__name__)

# Colunas obrigatórias do CSV
REQUIRED_COLUMNS = {"nome", "preco", "categoria"}
# Colunas opcionais com defaults
OPTIONAL_COLUMNS = {"disponivel": "true", "external_id": ""}


class CSVImport(InventorySync):
    """
    Importação de catálogo via arquivo CSV.

    Usa o campo external_id como chave de upsert.
    Se external_id for vazio, usa o nome como chave de deduplicação.
    """

    source_name = "csv"

    def __init__(self, db=None) -> None:
        self._db = db

    def parse_csv(self, content: str | bytes) -> list[ProductData]:
        """
        Parseia conteúdo CSV e retorna lista de ProductData.
        Tolera BOM UTF-8 e diferentes encodings.
        """
        if isinstance(content, bytes):
            content = content.decode("utf-8-sig")  # Remove BOM se existir

        reader = csv.DictReader(io.StringIO(content))
        rows = []

        # Normaliza nomes de colunas (strip + lower)
        fieldnames = [f.strip().lower() for f in (reader.fieldnames or [])]
        missing = REQUIRED_COLUMNS - set(fieldnames)
        if missing:
            raise ValueError(f"CSV está faltando colunas obrigatórias: {missing}")

        for i, row in enumerate(reader, start=2):
            # Normaliza keys
            row = {k.strip().lower(): v.strip() for k, v in row.items()}

            name = row.get("nome", "").strip()
            if not name:
                logger.warning("Linha %d ignorada: nome vazio", i)
                continue

            try:
                price = float(row.get("preco", "0").replace(",", "."))
            except (ValueError, AttributeError):
                logger.warning("Linha %d: preço inválido '%s' — usando 0", i, row.get("preco"))
                price = 0.0

            disponivel_str = row.get("disponivel", "true").lower()
            is_available = disponivel_str in ("true", "sim", "1", "yes", "s", "y")

            external_id = row.get("external_id", "").strip()
            if not external_id:
                # Fallback: usa nome como external_id para deduplicação
                external_id = name.lower().replace(" ", "_")

            rows.append(
                ProductData(
                    name=name,
                    price=price,
                    category_name=row.get("categoria", "Geral").strip() or "Geral",
                    external_id=external_id,
                    external_source=self.source_name,
                    is_available=is_available,
                    stock_quantity=None,
                    description=row.get("descricao", "").strip() or None,
                )
            )

        return rows

    async def import_from_content(
        self, tenant_id: uuid.UUID, content: str | bytes
    ) -> SyncResult:
        """Importa produtos de conteúdo CSV."""
        result = SyncResult(success=True)

        try:
            products = self.parse_csv(content)
        except ValueError as e:
            result.add_error(str(e))
            return result

        for product_data in products:
            try:
                from app.integrations._db_helper import upsert_product_from_data
                created = await upsert_product_from_data(tenant_id, product_data, self._db)
                if created:
                    result.created += 1
                else:
                    result.updated += 1
            except Exception as e:
                result.add_error(f"Produto '{product_data.name}': {e}")

        # Commit ao final
        if self._db:
            await self._db.commit()

        logger.info(
            "CSV import tenant=%s: criados=%d atualizados=%d erros=%d",
            tenant_id, result.created, result.updated, len(result.errors)
        )
        return result

    # Implementações ABC obrigatórias
    async def sync_all(self, tenant_id: uuid.UUID) -> SyncResult:
        raise NotImplementedError("CSVImport.sync_all: use import_from_content()")

    async def sync_product(self, tenant_id: uuid.UUID, external_id: str) -> ProductData | None:
        raise NotImplementedError("CSVImport não suporta sync por produto individual.")

    async def handle_webhook(self, tenant_id: uuid.UUID, payload: dict[str, Any]) -> SyncResult:
        raise NotImplementedError("CSVImport não suporta webhook.")

    async def validate_credentials(self, config: dict[str, Any]) -> bool:
        return True  # CSV não precisa de credenciais
