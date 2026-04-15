"""Schemas de produtos."""

import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class ProductCreate(BaseModel):
    name: str
    description: str | None = None
    price: float
    category_id: uuid.UUID
    stock_quantity: int | None = None
    is_available: bool = True

    @field_validator("price")
    @classmethod
    def price_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Preço não pode ser negativo.")
        return v


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    stock_quantity: int | None = None
    is_available: bool | None = None


class ProductResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    price: float
    category_id: uuid.UUID
    stock_quantity: int | None
    is_available: bool
    in_stock: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    sort_order: int
    is_active: bool
    products: list[ProductResponse] = []

    model_config = {"from_attributes": True}
