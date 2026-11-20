from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


def _blank(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be blank")
    return value


def _email(value: str) -> str:
    value = value.strip().lower()
    if value.count("@") != 1:
        raise ValueError("invalid email")
    local, domain = value.split("@")
    if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise ValueError("invalid email")
    return value


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    suggested_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)

    @field_validator("name", "description")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return _blank(value)


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1)
    suggested_price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)

    @field_validator("name", "description")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _blank(value)


class ServiceOut(BaseModel):
    id: int
    name: str
    description: str
    suggested_price: str


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return _blank(value)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _email(value)


class CustomerOut(BaseModel):
    id: int
    name: str
    email: str


class OrderCreate(BaseModel):
    customer_id: int
    service_id: int


class OrderOut(BaseModel):
    id: int
    customer_id: int
    service_id: int
    service_name: str
    service_description: str
    amount: str
    created_at: datetime
    canceled: bool


class LatestSale(BaseModel):
    order_id: int
    customer_id: int
    customer_name: str
    service_description: str
    amount: str
    created_at: datetime


class CustomerSales(BaseModel):
    customer_id: int
    customer_name: str
    order_count: int
    total_amount: str
