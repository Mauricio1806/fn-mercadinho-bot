"""Schemas de clientes."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class CustomerResponse(BaseModel):
    id: uuid.UUID
    phone: str
    name: str | None
    building_block: str | None
    apartment: str | None
    is_blocked: bool
    total_orders: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerUpdate(BaseModel):
    name: str | None = None
    building_block: str | None = None
    apartment: str | None = None
    notes: str | None = None
    is_blocked: bool | None = None
