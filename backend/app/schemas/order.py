"""Schemas de pedidos."""

import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models.order import OrderStatus


class OrderItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantidade deve ser maior que zero.")
        return v


class OrderCreate(BaseModel):
    customer_id: uuid.UUID
    items: list[OrderItemCreate]
    delivery_building_block: str | None = None
    delivery_apartment: str | None = None
    notes: str | None = None


class OrderItemResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    quantity: int
    unit_price: float
    subtotal: float

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    status: OrderStatus
    total_amount: float
    delivery_building_block: str | None
    delivery_apartment: str | None
    delivery_fee: float
    notes: str | None
    items: list[OrderItemResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
