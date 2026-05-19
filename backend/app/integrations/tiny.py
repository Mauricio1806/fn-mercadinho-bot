"""
Integração Tiny ERP — API key + polling.

Documentação: https://www.tiny.com.br/ajuda/api
Autenticação: API key fixa
Sync: polling a cada N minutos (configurável)
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx

from app.integrations.base import InventorySync, ProductData, SyncResult

logger = logging.getLogger(__name__)

TINY_API_BASE = "https://api.tiny.com.br/api2"


class TinySync(InventorySync):
    """
    Integração com Tiny ERP via API key.

    Config necessária no tenant:
    - integracao_estoque.api_key (token Tiny)
    - integracao_estoque.sync_intervalo_minutos
    """

    source_name = "tiny"

    def __init__(self, config: dict[str, Any], db=None) -> None:
        self._api_key = config.get("api_key", "")
        self._db = db

    async def _call(self, endpoint: str, params: dict) -> dict:
        params["token"] = self._api_key
        params["formato"] = "json"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{TINY_API_BASE}/{endpoint}.php", params=params)
            resp.raise_for_status()
            return resp.json()

    async def sync_all(self, tenant_id: uuid.UUID) -> SyncResult:
        result = SyncResult(success=True)
        pagina = 1

        while True:
            try:
                data = await self._call("produtos.pesquisa", {"pagina": pagina})
                retorno = data.get("retorno", {})

                if retorno.get("status") == "Erro":
                    result.add_error(retorno.get("erros", [{}])[0].get("erro", "Erro desconhecido"))
                    break

                produtos = retorno.get("produtos", [])
                if not produtos:
                    break

                for p_wrapper in produtos:
                    p = p_wrapper.get("produto", {})
                    try:
                        product_data = self._parse_product(p)
                        await self._upsert_product(tenant_id, product_data, result)
                    except Exception as e:
                        result.add_error(f"Produto {p.get('id', '?')}: {e}")

                pagina += 1
            except Exception as e:
                result.add_error(f"Página {pagina}: {e}")
                break

        logger.info(
            "Tiny sync_all tenant=%s: criados=%d atualizados=%d",
            tenant_id, result.created, result.updated
        )
        return result

    async def sync_product(self, tenant_id: uuid.UUID, external_id: str) -> ProductData | None:
        try:
            data = await self._call("produto.obter", {"id": external_id})
            retorno = data.get("retorno", {})
            if retorno.get("status") == "Erro":
                return None
            produto = retorno.get("produto", {})
            return self._parse_product(produto)
        except Exception as e:
            logger.error("Tiny sync_product %s: %s", external_id, e)
            return None

    async def handle_webhook(self, tenant_id: uuid.UUID, payload: dict[str, Any]) -> SyncResult:
        """Tiny não tem webhook nativo — ignora e retorna sucesso vazio."""
        return SyncResult(success=True)

    async def validate_credentials(self, config: dict[str, Any]) -> bool:
        api_key = config.get("api_key", "")
        if not api_key:
            return False
        try:
            data = await self._call("info", {})
            return data.get("retorno", {}).get("status") != "Erro"
        except Exception:
            return False

    def _parse_product(self, p: dict) -> ProductData:
        situacao = p.get("situacao", "A")
        qty_str = p.get("estoque", "0") or "0"
        try:
            qty = int(float(qty_str))
        except (ValueError, TypeError):
            qty = None

        categoria = p.get("categoria", {})
        nome_cat = categoria.get("descricao", "Geral") if isinstance(categoria, dict) else "Geral"

        return ProductData(
            name=p.get("descricao", "Sem nome"),
            price=float(p.get("preco", 0) or 0),
            category_name=nome_cat,
            external_id=str(p.get("id", "")),
            external_source=self.source_name,
            is_available=situacao == "A" and (qty is None or qty > 0),
            stock_quantity=qty,
            description=p.get("descricaoComplementar"),
        )

    async def _upsert_product(
        self, tenant_id: uuid.UUID, data: ProductData, result: SyncResult
    ) -> None:
        from app.integrations._db_helper import upsert_product_from_data
        created = await upsert_product_from_data(tenant_id, data, self._db)
        if created:
            result.created += 1
        else:
            result.updated += 1
