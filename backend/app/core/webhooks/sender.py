"""Sender de webhooks outbound com retry exponencial."""
from __future__ import annotations
import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.webhooks.security import sign_payload, decrypt_secret, payload_hash
from app.models.webhook import WebhookEndpoint, WebhookDelivery, WebhookDirection, DeliveryStatus

logger = logging.getLogger(__name__)
RETRY_DELAYS = [1, 5, 30, 300, 3600]
TIMEOUT = 10.0


async def dispatch_event(db: AsyncSession, tenant_id: UUID, event_type: str, event_data: dict) -> int:
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.tenant_id == tenant_id,
            WebhookEndpoint.direction == WebhookDirection.OUTBOUND.value,
            WebhookEndpoint.active == True,
            WebhookEndpoint.events.any(event_type),
        )
    )
    endpoints = result.scalars().all()
    for ep in endpoints:
        asyncio.create_task(_send_with_retry(ep.id, event_type, event_data, tenant_id))
    return len(endpoints)


async def _send_with_retry(endpoint_id: UUID, event_type: str, event_data: dict, tenant_id: UUID) -> None:
    from app.database.session import AsyncSessionLocal
    payload = json.dumps({"id": str(uuid4()), "event": event_type,
                          "timestamp": datetime.now(timezone.utc).isoformat(),
                          "tenant_id": str(tenant_id), "data": event_data},
                         separators=(",", ":")).encode()
    body_hash = payload_hash(payload)

    for attempt in range(1, len(RETRY_DELAYS) + 2):
        async with AsyncSessionLocal() as db:
            ep = await db.get(WebhookEndpoint, endpoint_id)
            if not ep or not ep.active:
                return
            secret = decrypt_secret(ep.secret_encrypted)
            sig, ts = sign_payload(payload, secret)
            headers = {"Content-Type": "application/json",
                       "X-Atende-Signature": f"t={ts},v1={sig}",
                       "X-Atende-Event": event_type}
            start = time.monotonic()
            status = DeliveryStatus.FAILED.value
            response_status = None
            error = None
            try:
                async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                    resp = await client.post(ep.url, content=payload, headers=headers)
                    response_status = resp.status_code
                    status = DeliveryStatus.SUCCESS.value if 200 <= resp.status_code < 300 else DeliveryStatus.FAILED.value
            except Exception as e:
                error = str(e)[:500]
            db.add(WebhookDelivery(
                tenant_id=tenant_id, endpoint_id=endpoint_id,
                direction=WebhookDirection.OUTBOUND.value, event_type=event_type,
                payload_hash=body_hash, response_status=response_status,
                duration_ms=int((time.monotonic() - start) * 1000),
                attempt=attempt, status=status, error_message=error,
            ))
            await db.commit()
            if status == DeliveryStatus.SUCCESS.value:
                return
        if attempt <= len(RETRY_DELAYS):
            await asyncio.sleep(RETRY_DELAYS[attempt - 1])
