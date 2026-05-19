"""Schemas de tenant para a API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.tenancy.config_schema import TenantConfig


class TenantCreate(BaseModel):
    slug: str
    name: str
    whatsapp_number: str | None = None
    config: dict

    @field_validator("slug")
    @classmethod
    def slug_format(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("slug deve conter apenas minúsculas, números e hífens.")
        return v

    @field_validator("config")
    @classmethod
    def validate_config(cls, v: dict) -> dict:
        TenantConfig(**v)  # Valida antes de salvar
        return v


class TenantUpdate(BaseModel):
    name: str | None = None
    whatsapp_number: str | None = None
    is_active: bool | None = None
    config: dict | None = None  # Merge parcial — não substitui tudo


class TenantOut(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    whatsapp_number: str | None
    is_active: bool
    config: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TenantSummary(BaseModel):
    """Versão resumida para listagem."""
    id: uuid.UUID
    slug: str
    name: str
    whatsapp_number: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
