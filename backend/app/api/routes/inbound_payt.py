"""Endpoint inbound para postbacks Payt — cart recovery multi-tenant."""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.recoverable_sale import RecoverableSale, RecoveryFunnelStage, RecoverySaleStatus
from app.tenancy.resolver import resolve_tenant_by_slug

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Resultado do parser ────────────────────────────────────────────────────────

class ParseAction(str, Enum):
    ENQUEUE = "enqueue"
    RESOLVE = "resolve"
    DISCARD = "discard"


@dataclass
class ParseResult:
    action: ParseAction
    reason: str = ""
    # campos para ENQUEUE
    external_id: str = ""
    funnel_stage: RecoveryFunnelStage | None = None
    customer_name: str | None = None
    customer_phone: str = ""
    product_name: str | None = None
    amount: float = 0.0
    checkout_url: str | None = None
    pix_code: str | None = None
    coupon: str | None = None
    expires_at: datetime | None = None
    attribution: dict = field(default_factory=dict)
    # campos para RESOLVE
    new_status: RecoverySaleStatus | None = None


# ── Normalização de telefone ───────────────────────────────────────────────────

def normalize_phone(raw: str) -> str | None:
    """
    Converte telefone para E.164 sem '+'.
    011999998888 → 5511999998888
    11999998888  → 5511999998888
    5511999998888 → 5511999998888
    """
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    # Remove zero de tronco (0xx)
    if digits.startswith("0"):
        digits = digits[1:]
    # Adiciona DDI 55 se não tem código de país (≤11 dígitos → DDD+número BR)
    if len(digits) <= 11:
        digits = "55" + digits
    if len(digits) < 10:
        return None
    return digits


# ── Parser Payt V1 ─────────────────────────────────────────────────────────────

def parse_payt_postback(payload: dict[str, Any]) -> ParseResult:
    """
    Classifica um postback Payt V1 em ENQUEUE, RESOLVE ou DISCARD.

    Ordem de avaliação:
    1. test=true                    → DISCARD
    2. status=paid                  → RESOLVE recovered  (tem precedência sobre cart_recovered)
    3. status=expired|canceled      → RESOLVE expired/lost
    4. customer.phone vazio         → DISCARD
    5. cart_recovered=true          → DISCARD
    6. status=waiting_payment+pix   → ENQUEUE pix_pendente
    7. type=abandoned-cart|lost_cart→ ENQUEUE abandono
    """
    pay_status = (payload.get("status") or "").lower()
    event_type = (payload.get("type") or "").lower()

    # 1. Descarta testes
    if payload.get("test") is True:
        return ParseResult(action=ParseAction.DISCARD, reason="test=true")

    # Extrai external_id: transaction.id > cart_id
    transaction = payload.get("transaction") or {}
    external_id = str(transaction.get("id") or payload.get("cart_id") or "").strip()
    if not external_id:
        return ParseResult(action=ParseAction.DISCARD, reason="external_id ausente")

    # 2. RESOLVE — paid (tem precedência sobre cart_recovered)
    if pay_status == "paid":
        return ParseResult(
            action=ParseAction.RESOLVE,
            reason="status=paid",
            external_id=external_id,
            new_status=RecoverySaleStatus.RECOVERED,
        )

    # 3. RESOLVE — expired / canceled
    if pay_status == "expired":
        return ParseResult(
            action=ParseAction.RESOLVE,
            reason="status=expired",
            external_id=external_id,
            new_status=RecoverySaleStatus.EXPIRED,
        )
    if pay_status == "canceled":
        return ParseResult(
            action=ParseAction.RESOLVE,
            reason="status=canceled",
            external_id=external_id,
            new_status=RecoverySaleStatus.LOST,
        )

    # 4. Descarta telefone vazio
    customer = payload.get("customer") or {}
    raw_phone = str(customer.get("phone") or "").strip()
    phone = normalize_phone(raw_phone)
    if not phone:
        return ParseResult(action=ParseAction.DISCARD, reason="customer.phone vazio")

    # 5. Descarta carrinho já recuperado
    if payload.get("cart_recovered") is True:
        return ParseResult(action=ParseAction.DISCARD, reason="cart_recovered=true")

    # Dados comuns para ENQUEUE
    payment_method = (payload.get("payment_method") or "").lower()
    total_cents = transaction.get("total_price") or payload.get("total_price") or 0
    try:
        amount = float(total_cents) / 100.0
    except (TypeError, ValueError):
        amount = 0.0

    customer_name = str(customer.get("name") or "").strip() or None

    # Produto: primeiro item do cart, se existir
    items = payload.get("cart") or payload.get("items") or []
    product_name: str | None = None
    if items and isinstance(items, list):
        first = items[0] if items else {}
        product_name = str(first.get("name") or first.get("nome") or "").strip() or None

    attribution = {
        k: payload.get(k)
        for k in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")
        if payload.get(k)
    }

    # 6. ENQUEUE — Pix pendente
    if pay_status == "waiting_payment" and payment_method == "pix":
        pix_data = transaction.get("pix") or {}
        checkout_url = transaction.get("pix_url") or pix_data.get("url")
        pix_code = pix_data.get("code") or pix_data.get("qr_code")

        expires_at: datetime | None = None
        raw_exp = pix_data.get("expires_at") or transaction.get("expires_at")
        if raw_exp:
            try:
                if isinstance(raw_exp, (int, float)):
                    expires_at = datetime.fromtimestamp(raw_exp, tz=timezone.utc)
                else:
                    expires_at = datetime.fromisoformat(str(raw_exp).replace("Z", "+00:00"))
            except (ValueError, OSError):
                pass

        return ParseResult(
            action=ParseAction.ENQUEUE,
            reason="pix_pendente",
            external_id=external_id,
            funnel_stage=RecoveryFunnelStage.PIX_PENDENTE,
            customer_name=customer_name,
            customer_phone=phone,
            product_name=product_name,
            amount=amount,
            checkout_url=checkout_url,
            pix_code=pix_code,
            expires_at=expires_at,
            attribution=attribution,
        )

    # 7. ENQUEUE — Abandono de carrinho
    if event_type == "abandoned-cart" or pay_status == "lost_cart":
        link = payload.get("link") or {}
        checkout_url_ab = link.get("url") or payload.get("checkout_url")
        coupons = link.get("available_coupons") or []
        coupon = coupons[0].get("code") if coupons and isinstance(coupons[0], dict) else (
            coupons[0] if coupons else None
        )

        return ParseResult(
            action=ParseAction.ENQUEUE,
            reason="abandono",
            external_id=external_id,
            funnel_stage=RecoveryFunnelStage.ABANDONO,
            customer_name=customer_name,
            customer_phone=phone,
            product_name=product_name,
            amount=amount,
            checkout_url=checkout_url_ab,
            coupon=coupon,
            attribution=attribution,
        )

    return ParseResult(action=ParseAction.DISCARD, reason=f"evento não mapeado: type={event_type} status={pay_status}")


# ── Operações de banco ─────────────────────────────────────────────────────────

async def _upsert_recoverable_sale(
    tenant_id: uuid.UUID,
    result: ParseResult,
    db: AsyncSession,
) -> None:
    """Cria ou atualiza um recoverable_sale (upsert por tenant_id + external_id)."""
    now = datetime.now(tz=timezone.utc)

    existing = await db.execute(
        select(RecoverableSale).where(
            RecoverableSale.tenant_id == str(tenant_id),
            RecoverableSale.external_id == result.external_id,
        )
    )
    sale = existing.scalar_one_or_none()

    if sale is None:
        sale = RecoverableSale(
            tenant_id=str(tenant_id),
            source="payt",
            external_id=result.external_id,
            customer_name=result.customer_name,
            customer_phone=result.customer_phone,
            product_name=result.product_name,
            amount=result.amount,
            checkout_url=result.checkout_url,
            pix_code=result.pix_code,
            coupon=result.coupon,
            expires_at=result.expires_at,
            attribution=result.attribution,
            status=RecoverySaleStatus.PENDING,
            funnel_stage=result.funnel_stage,
            abandoned_at=now,
        )
        db.add(sale)
    else:
        # Atualiza campos que podem mudar (ex: novo cupom, nova URL)
        if result.checkout_url:
            sale.checkout_url = result.checkout_url
        if result.coupon:
            sale.coupon = result.coupon
        if result.expires_at:
            sale.expires_at = result.expires_at
        if result.pix_code:
            sale.pix_code = result.pix_code

    await db.commit()


async def _resolve_recoverable_sale(
    tenant_id: uuid.UUID,
    external_id: str,
    new_status: RecoverySaleStatus,
    db: AsyncSession,
) -> bool:
    """Atualiza o status de uma venda existente. Retorna True se encontrou."""
    existing = await db.execute(
        select(RecoverableSale).where(
            RecoverableSale.tenant_id == str(tenant_id),
            RecoverableSale.external_id == external_id,
        )
    )
    sale = existing.scalar_one_or_none()
    if sale is None:
        return False
    sale.status = new_status
    await db.commit()
    return True


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post("/{tenant_slug}/payt", status_code=status.HTTP_200_OK)
async def inbound_payt(
    tenant_slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Recebe postback Payt V1 para um tenant específico (identificado pelo slug).

    Autenticação: integration_key no corpo JSON contra tenant.config["payt"]["integration_key"].
    Retorna 200 em todos os casos válidos — o Payt não deve fazer retry por erros de negócio.
    """
    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload inválido.")

    # Resolve tenant por slug
    tenant_ctx = await resolve_tenant_by_slug(tenant_slug, db)
    if tenant_ctx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado.")

    # Valida integration_key contra config do tenant
    # Busca o Tenant ORM para acessar config raw
    from app.models.tenant import Tenant
    result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug, Tenant.is_active == True)  # noqa: E712
    )
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado.")

    payt_config = (tenant.config or {}).get("payt") or {}
    expected_key = payt_config.get("integration_key") or ""
    received_key = str(payload.get("integration_key") or "").strip()

    if expected_key and received_key != expected_key:
        logger.warning(
            "integration_key inválida para tenant=%s (recebida=%s)",
            tenant_slug,
            received_key[:8] + "..." if len(received_key) > 8 else received_key,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="integration_key inválida.",
        )

    # Parse do payload
    parse_result = parse_payt_postback(payload)
    logger.info(
        "Payt inbound | tenant=%s action=%s reason=%s",
        tenant_slug, parse_result.action.value, parse_result.reason,
    )

    if parse_result.action == ParseAction.DISCARD:
        return {"status": "discarded", "reason": parse_result.reason}

    if parse_result.action == ParseAction.RESOLVE:
        found = await _resolve_recoverable_sale(
            tenant.id, parse_result.external_id, parse_result.new_status, db  # type: ignore[arg-type]
        )
        if not found:
            logger.debug("RESOLVE sem linha existente — external_id=%s", parse_result.external_id)
        return {"status": "resolved", "new_status": (parse_result.new_status or RecoverySaleStatus.RECOVERED).value}

    # ENQUEUE
    await _upsert_recoverable_sale(tenant.id, parse_result, db)  # type: ignore[arg-type]
    return {"status": "queued", "funnel_stage": (parse_result.funnel_stage or RecoveryFunnelStage.ABANDONO).value}
