from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models import LotStatus, UserRole


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    role: UserRole


class UserRead(UserCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AuctionCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str | None = None
    starts_at: datetime
    ends_at: datetime
    organizer_id: int

    @model_validator(mode="after")
    def validate_period(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be later than starts_at")
        return self


class AuctionRead(AuctionCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LotCreate(BaseModel):
    seller_id: int
    title: str = Field(min_length=2, max_length=160)
    description: str | None = None
    start_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    min_increment: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class LotRead(LotCreate):
    id: int
    auction_id: int
    status: LotStatus
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BidCreate(BaseModel):
    buyer_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class BidRead(BidCreate):
    id: int
    lot_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SaleRead(BaseModel):
    id: int
    lot_id: int
    buyer_id: int
    seller_id: int
    final_price: Decimal
    sold_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RevenueRow(BaseModel):
    seller_id: int
    seller_name: str
    sales_count: int
    revenue: Decimal
