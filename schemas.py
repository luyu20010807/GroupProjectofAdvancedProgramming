from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class CartAddRequest(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=99)


class CheckoutRequest(BaseModel):
    receiver_name: str = Field(min_length=2, max_length=80)
    receiver_phone: str = Field(min_length=6, max_length=30)
    receiver_address: str = Field(min_length=5, max_length=255)
    remark: str = Field(default="", max_length=255)


class RefundApplyRequest(BaseModel):
    refund_type: str = Field(pattern="^(refund_only|return_refund)$")
    reason: str = Field(min_length=2, max_length=255)
    description: str = Field(default="", max_length=1000)
