"""Webhook — recebe mensagens do bridge e despacha pro ConversationEngine."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.platform.conversation.engine import ConversationEngine
from app.platform.whatsapp.webhook_parser import parse_whatsapp_message
from app.tenancy.resolver import resolve_tenant_by_number

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/")
async def receive_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    try:
        import json
        body = await request.body()
        payload: dict[str, Any] = json.loads(body)
    except Exception:
        return {"status": "invalid_payload"}

    print("PAYLOAD RAW:", payload, flush=True)

    inbound = parse_whatsapp_message(payload)
    if inbound is None:
        return {"status": "ignored"}

    # ── Resolve tenant pelo número que recebeu a mensagem ────────────────────
    to_number = getattr(inbound, "to_number", None) or payload.get("to_number", "")
    tenant_ctx = await resolve_tenant_by_number(to_number, db)

    if tenant_ctx is None:
        # Fallback: tenta resolver pelo número fixo do FN enquanto migração não está completa
        logger.warning(
            "Tenant não encontrado para %s — usando fallback FN Mercadinho", to_number
        )
        from app.tenancy.resolver import resolve_tenant_by_number as _r
        tenant_ctx = await _r("557199371599", db)

    if tenant_ctx is None:
        logger.error("Nenhum tenant disponível — mensagem descartada")
        return {"status": "tenant_not_found"}

    # ── Dispara engine com contexto do tenant ────────────────────────────────
    try:
        engine = ConversationEngine(db=db, tenant=tenant_ctx)
        await engine.handle(inbound)
    except Exception as e:
        import traceback
        print("ERRO WEBHOOK:", e, flush=True)
        traceback.print_exc()

    return {"status": "processed"}
