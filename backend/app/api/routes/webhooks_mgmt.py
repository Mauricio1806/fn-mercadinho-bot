"""
Gestão de webhooks por tenant.
CRUD de endpoints + receiver inbound + log de deliveries.
"""
from __future__ import annotations
import json
import time
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.tenant_scope import get_current_role
from app.database.session import get_db
from app.models.webhook import (
    WebhookEndpoint, WebhookDelivery, WebhookIdempotency,
    WebhookDirection, DeliveryStatus,
)
from app.core.webhooks.security import (
    encrypt_secret, decrypt_secret, generate_secret,
    verify_signature, parse_signature_header, payload_hash,
)

router = APIRouter()


def require_superadmin(role: str = Depends(get_current_role)) -> str:
    if role != "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas superadmin.")
    return role


class EndpointCreate(BaseModel):
    name: str
    direction: str
    slug: str | None = None
    url: str | None = None
    events: list[str] = []
    allowed_ips: list[str] | None = None
    max_per_minute: int = 100


class EndpointUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    events: list[str] | None = None
    active: bool | None = None
    allowed_ips: list[str] | None = None
    max_per_minute: int | None = None


class EndpointOut(BaseModel):
    id: str
    name: str
    direction: str
    slug: str | None
    url: str | None
    events: list[str]
    active: bool
    secret: str | None = None


@router.post("/{tenant_id}/endpoints", status_code=status.HTTP_201_CREATED, response_model=EndpointOut)
async def create_endpoint(
    tenant_id: UUID,
    body: EndpointCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_superadmin),
) -> EndpointOut:
    if body.direction == "outbound" and not body.url:
        raise HTTPException(status_code=400, detail="Webhook outbound exige campo 'url'.")
    if body.direction == "inbound" and not body.slug:
        raise HTTPException(status_code=400, detail="Webhook inbound exige campo 'slug'.")

    secret_plain = generate_secret()
    endpoint = WebhookEndpoint(
        id=uuid4(),
        tenant_id=tenant_id,
        name=body.name,
        direction=body.direction,
        slug=body.slug,
        url=body.url,
        secret_encrypted=encrypt_secret(secret_plain),
        events=body.events,
        allowed_ips=body.allowed_ips,
        max_per_minute=body.max_per_minute,
    )
    db.add(endpoint)
    await db.commit()
    await db.refresh(endpoint)

    return EndpointOut(
        id=str(endpoint.id), name=endpoint.name, direction=endpoint.direction,
        slug=endpoint.slug, url=endpoint.url, events=endpoint.events,
        active=endpoint.active, secret=secret_plain,
    )


@router.get("/{tenant_id}/endpoints", response_model=list[EndpointOut])
async def list_endpoints(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_superadmin),
) -> list[EndpointOut]:
    result = await db.execute(
        select(WebhookEndpoint).where(WebhookEndpoint.tenant_id == tenant_id)
    )
    items = result.scalars().all()
    return [EndpointOut(
        id=str(e.id), name=e.name, direction=e.direction, slug=e.slug,
        url=e.url, events=e.events, active=e.active,
    ) for e in items]


@router.patch("/{tenant_id}/endpoints/{endpoint_id}", response_model=EndpointOut)
async def update_endpoint(
    tenant_id: UUID, endpoint_id: UUID,
    body: EndpointUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_superadmin),
) -> EndpointOut:
    ep = await db.get(WebhookEndpoint, endpoint_id)
    if not ep or str(ep.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=404, detail="Endpoint não encontrado.")
    if body.name is not None: ep.name = body.name
    if body.url is not None: ep.url = body.url
    if body.events is not None: ep.events = body.events
    if body.active is not None: ep.active = body.active
    if body.allowed_ips is not None: ep.allowed_ips = body.allowed_ips
    if body.max_per_minute is not None: ep.max_per_minute = body.max_per_minute
    await db.commit()
    await db.refresh(ep)
    return EndpointOut(
        id=str(ep.id), name=ep.name, direction=ep.direction, slug=ep.slug,
        url=ep.url, events=ep.events, active=ep.active,
    )


@router.delete("/{tenant_id}/endpoints/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_endpoint(
    tenant_id: UUID, endpoint_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_superadmin),
) -> None:
    ep = await db.get(WebhookEndpoint, endpoint_id)
    if not ep or str(ep.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=404, detail="Endpoint não encontrado.")
    await db.delete(ep)
    await db.commit()


@router.get("/{tenant_id}/deliveries")
async def list_deliveries(
    tenant_id: UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_superadmin),
) -> list[dict]:
    result = await db.execute(
        select(WebhookDelivery)
        .where(WebhookDelivery.tenant_id == tenant_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(limit)
    )
    items = result.scalars().all()
    return [{
        "id": str(d.id),
        "direction": d.direction,
        "event_type": d.event_type,
        "status": d.status,
        "response_status": d.response_status,
        "duration_ms": d.duration_ms,
        "attempt": d.attempt,
        "error_message": d.error_message,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    } for d in items]


@router.post("/inbound/{tenant_id}/{slug}")
async def receive_inbound(
    tenant_id: UUID,
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    start = time.monotonic()
    body = await request.body()
    source_ip = request.client.host if request.client else "unknown"

    if len(body) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Payload muito grande (max 10MB).")

    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.tenant_id == tenant_id,
            WebhookEndpoint.slug == slug,
            WebhookEndpoint.direction == WebhookDirection.INBOUND.value,
            WebhookEndpoint.active == True,
        )
    )
    ep = result.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="Webhook endpoint não encontrado.")

    if ep.allowed_ips and source_ip not in ep.allowed_ips:
        raise HTTPException(status_code=403, detail="IP não permitido.")

    sig_header = request.headers.get("X-Atende-Signature", "")
    parsed = parse_signature_header(sig_header)
    if not parsed:
        raise HTTPException(status_code=401, detail="Assinatura ausente ou inválida.")

    ts, sig = parsed
    secret = decrypt_secret(ep.secret_encrypted)
    if not verify_signature(body, sig, ts, secret):
        raise HTTPException(status_code=401, detail="Assinatura inválida.")

    body_hash_str = payload_hash(body)
    existing = await db.get(WebhookIdempotency, body_hash_str)
    if existing:
        return {"status": "duplicate", "key": body_hash_str}

    db.add(WebhookIdempotency(key=body_hash_str, tenant_id=tenant_id))

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Body não é JSON válido.")

    event_type = payload.get("event") or request.headers.get("X-Event-Type", "unknown")
    duration_ms = int((time.monotonic() - start) * 1000)

    db.add(WebhookDelivery(
        tenant_id=tenant_id,
        endpoint_id=ep.id,
        direction=WebhookDirection.INBOUND.value,
        event_type=event_type,
        payload_hash=body_hash_str,
        request_headers=dict(request.headers),
        request_body=body.decode(errors="replace")[:10000],
        attempt=1,
        status=DeliveryStatus.SUCCESS.value,
        source_ip=source_ip,
        duration_ms=duration_ms,
    ))
    await db.commit()

    return {"status": "received", "event": event_type, "key": body_hash_str}
