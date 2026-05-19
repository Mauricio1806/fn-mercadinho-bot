"""Rotas de integração de estoque — webhook ERP + upload CSV."""

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_tenant_admin
from app.api.middleware.tenant_scope import TenantScope, get_tenant_scope
from app.database.session import get_db
from app.models.admin_user import AdminUser
from app.models.tenant import Tenant

router = APIRouter()


def _get_integration_handler(tenant: Tenant, db: AsyncSession):
    """Retorna o handler de integração correto baseado no config do tenant."""
    config = tenant.config or {}
    integracao = config.get("integracao_estoque", {})
    sistema = integracao.get("sistema")

    if sistema == "bling":
        from app.integrations.bling import BlingSync
        return BlingSync(integracao, db)
    elif sistema == "tiny":
        from app.integrations.tiny import TinySync
        return TinySync(integracao, db)
    elif sistema == "webhook":
        from app.integrations.generic_webhook import GenericWebhookSync
        return GenericWebhookSync(db)
    else:
        from app.integrations.generic_webhook import GenericWebhookSync
        return GenericWebhookSync(db)


@router.post("/{tenant_id}/webhook")
async def receive_erp_webhook(
    tenant_id: uuid.UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Recebe webhook de sistema ERP externo e atualiza produto em tempo real.
    Este endpoint é público (sem auth JWT) — o ERP chama diretamente.
    Segurança via tenant_id na URL + secret opcional no payload.
    """
    from sqlalchemy import select

    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.is_active == True)  # noqa: E712
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado.")

    handler = _get_integration_handler(tenant, db)
    sync_result = await handler.handle_webhook(tenant_id, payload)

    return {
        "status": "ok" if sync_result.success else "partial",
        "created": sync_result.created,
        "updated": sync_result.updated,
        "errors": sync_result.errors[:5],  # Limita a 5 erros na resposta
    }


@router.post("/{tenant_id}/csv")
async def import_csv(
    tenant_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    scope: TenantScope = Depends(get_tenant_scope),
    _: AdminUser = Depends(get_current_tenant_admin),
) -> dict:
    """
    Importa catálogo via CSV. Faz upsert de produtos.

    Formato CSV:
    nome,preco,categoria,disponivel,external_id

    O campo external_id é usado para deduplicação (upsert).
    Se vazio, o nome do produto é usado como chave.
    """
    # Valida que o usuário tem acesso a este tenant
    scope.assert_owns_tenant(tenant_id)

    # Valida tipo do arquivo
    if file.content_type not in ("text/csv", "text/plain", "application/csv",
                                  "application/vnd.ms-excel"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo deve ser CSV (.csv ou .txt)",
        )

    content = await file.read()

    # Limita a 10MB
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Arquivo CSV muito grande (máximo 10MB).",
        )

    from app.integrations.csv_import import CSVImport
    importer = CSVImport(db)
    result = await importer.import_from_content(tenant_id, content)

    return {
        "status": "ok" if result.success else "partial",
        "created": result.created,
        "updated": result.updated,
        "total_processed": result.total_processed,
        "errors": result.errors[:10],
    }


@router.post("/{tenant_id}/sync")
async def trigger_full_sync(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    scope: TenantScope = Depends(get_tenant_scope),
    _: AdminUser = Depends(get_current_tenant_admin),
) -> dict:
    """Dispara sincronização completa do ERP configurado (Bling/Tiny)."""
    scope.assert_owns_tenant(tenant_id)

    from sqlalchemy import select
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado.")

    config = (tenant.config or {}).get("integracao_estoque", {})
    if not config.get("ativo"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integração de estoque não está ativa para este tenant.",
        )

    handler = _get_integration_handler(tenant, db)
    sync_result = await handler.sync_all(tenant_id)

    return {
        "status": "ok" if sync_result.success else "partial",
        "created": sync_result.created,
        "updated": sync_result.updated,
        "errors": sync_result.errors[:10],
    }
