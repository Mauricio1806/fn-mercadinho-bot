"""Models de webhooks."""
from __future__ import annotations
from datetime import datetime
import enum
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin


class WebhookDirection(str, enum.Enum):
    INBOUND  = "inbound"
    OUTBOUND = "outbound"


class DeliveryStatus(str, enum.Enum):
    SUCCESS  = "success"
    FAILED   = "failed"
    RETRYING = "retrying"


class WebhookEndpoint(UUIDMixin, Base):
    __tablename__ = "webhook_endpoints"

    tenant_id:        Mapped[str]       = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    name:             Mapped[str]       = mapped_column(String(100), nullable=False)
    direction:        Mapped[str]       = mapped_column(String(20), nullable=False)
    slug:             Mapped[str|None]  = mapped_column(String(100), nullable=True)
    url:              Mapped[str|None]  = mapped_column(String(500), nullable=True)
    secret_encrypted: Mapped[str]       = mapped_column(Text, nullable=False)
    events:           Mapped[list]      = mapped_column(ARRAY(String(50)), default=list, nullable=False)
    active:           Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)
    allowed_ips:      Mapped[list|None] = mapped_column(ARRAY(String(50)), nullable=True)
    max_per_minute:   Mapped[int]       = mapped_column(Integer, default=100, nullable=False)
    created_at:       Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at:       Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class WebhookDelivery(UUIDMixin, Base):
    __tablename__ = "webhook_deliveries"

    tenant_id:       Mapped[str]      = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    endpoint_id:     Mapped[str|None] = mapped_column(UUID(as_uuid=True), ForeignKey("webhook_endpoints.id"), nullable=True)
    direction:       Mapped[str]      = mapped_column(String(20), nullable=False)
    event_type:      Mapped[str|None] = mapped_column(String(100), nullable=True)
    payload_hash:    Mapped[str]      = mapped_column(String(64), nullable=False)
    request_headers: Mapped[dict|None]= mapped_column(JSONB, nullable=True)
    request_body:    Mapped[str|None] = mapped_column(Text, nullable=True)
    response_status: Mapped[int|None] = mapped_column(Integer, nullable=True)
    response_body:   Mapped[str|None] = mapped_column(Text, nullable=True)
    duration_ms:     Mapped[int|None] = mapped_column(Integer, nullable=True)
    attempt:         Mapped[int]      = mapped_column(Integer, default=1, nullable=False)
    status:          Mapped[str]      = mapped_column(String(20), nullable=False)
    error_message:   Mapped[str|None] = mapped_column(Text, nullable=True)
    source_ip:       Mapped[str|None] = mapped_column(String(50), nullable=True)
    created_at:      Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WebhookIdempotency(Base):
    __tablename__ = "webhook_idempotency"

    key:          Mapped[str]      = mapped_column(String(128), primary_key=True)
    tenant_id:    Mapped[str]      = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
