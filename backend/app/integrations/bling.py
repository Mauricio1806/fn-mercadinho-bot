"""
Integração Bling ERP — OAuth2 + webhook em tempo real.

Documentação: https://developer.bling.com.br/
Autenticação: OAuth2 com refresh token
Webhook: Bling envia POST para /api/integrations/{tenant_id}/webhook
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx

from app.integrations.base import InventorySync, ProductData, SyncResult

logger = logging.getLogger(__name__)

BLING_API_BASE = "https://www.bling.com.br/Api/v3"
BLING_TOKEN_URL = "https://www.bling.com.br/Api/v3/oauth/token"


class BlingSync(InventorySync):
    """
    Integração com Bling ERP via OAuth2.

    Config necessária no tenant:
    - integracao_estoque.client_id
    - integracao_estoque.client_secret
    - integracao_estoque.api_key (access token — renovado via refresh)
    """

    source_name = "bling"

    def __init__(self, config: dict[str, Any], db=None) -> None:
        self._config = config
        self._db = db
        self._access_token: str | None = config.get("api_key")

    async def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
        }

    async def _fetch_products_page(self, page: int = 1) -> dict:
        """Busca uma página de produtos do Bling."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{BLING_API_BASE}/produtos",
                headers=await self._get_headers(),
                params={"pagina": page, "limite": 100},
            )
            resp.raise_for_status()
            return resp.json()

    async def sync_all(self, tenant_id: uuid.UUID) -> SyncResult:
        result = SyncResult(success=True)
        page = 1

        while True:
            try:
                data = await self._fetch_products_page(page)
                items = data.get("data", [])
                if not items:
                    break

                for item in items:
                    try:
                        product_data = self._parse_product(item)
                        await self._upsert_product(tenant_id, product_data, result)
                    except Exception as e:
                        result.add_error(f"Produto {item.get('id', '?')}: {e}")

                page += 1
            except Exception as e:
                result.add_error(f"Página {page}: {e}")
                break

        logger.info(
            "Bling sync_all tenant=%s: criados=%d atualizados=%d erros=%d",
            tenant_id, result.created, result.updated, len(result.errors),
        )
        return result

    async def sync_product(self, tenant_id: uuid.UUID, external_id: str) -> ProductData | None:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{BLING_API_BASE}/produtos/{external_id}",
                    headers=await self._get_headers(),
                )
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                data = resp.json().get("data", {})
                return self._parse_product(data)
        except Exception as e:
            logger.error("Bling sync_product %s: %s", external_id, e)
            return None

    async def handle_webhook(self, tenant_id: uuid.UUID, payload: dict[str, Any]) -> SyncResult:
        """
        Processa evento do Bling.
        Tipos suportados: produto_alterado, produto_excluido, estoque_alterado
        """
        result = SyncResult(success=True)
        event_type = payload.get("evento", "")
        product_id = str(payload.get("dados", {}).get("id", ""))

        if not product_id:
            result.add_error("Payload sem dados.id")
            return result

        if event_type in ("produto_alterado", "estoque_alterado"):
            product_data = await self.sync_product(tenant_id, product_id)
            if product_data:
                await self._upsert_product(tenant_id, product_data, result)

        elif event_type == "produto_excluido":
            await self._mark_unavailable(tenant_id, product_id)
            result.updated = 1

        return result

    async def validate_credentials(self, config: dict[str, Any]) -> bool:
        token = config.get("api_key", "")
        if not token:
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{BLING_API_BASE}/usuarios/me",
                    headers={"Authorization": f"Bearer {token}"},
                )
                return resp.status_code == 200
        except Exception:
            return False

    def _parse_product(self, item: dict) -> ProductData:
        """Converte formato Bling para ProductData normalizado."""
        categoria = item.get("categoria", {})
        nome_categoria = categoria.get("descricao", "Geral") if categoria else "Geral"

        estoque = item.get("estoque", {})
        qty = None
        if estoque:
            qty = int(estoque.get("saldoVirtualTotal", 0) or 0)

        preco = float(item.get("preco", 0) or 0)
        situacao = item.get("situacao", "A")

        return ProductData(
            name=item.get("nome", "Sem nome"),
            price=preco,
            category_name=nome_categoria,
            external_id=str(item.get("id", "")),
            external_source=self.source_name,
            is_available=situacao == "A" and (qty is None or qty > 0),
            stock_quantity=qty,
            description=item.get("descricaoCurta"),
        )

    async def _upsert_product(
        self, tenant_id: uuid.UUID, data: ProductData, result: SyncResult
    ) -> None:
        """Faz upsert do produto no banco — delega para o serviço central."""
        from app.integrations._db_helper import upsert_product_from_data
        created = await upsert_product_from_data(tenant_id, data, self._db)
        if created:
            result.created += 1
        else:
            result.updated += 1

    async def _mark_unavailable(self, tenant_id: uuid.UUID, external_id: str) -> None:
        from app.integrations._db_helper import mark_product_unavailable
        await mark_product_unavailable(tenant_id, external_id, self._db)
