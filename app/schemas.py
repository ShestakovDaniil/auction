from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import AuctionStatus, LotStatus, UserRole


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: UserRole = UserRole.BUYER


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    role: UserRole
    created_at: datetime


class LotCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    start_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class LotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    start_price: Decimal
    seller_id: int
    status: LotStatus
    created_at: datetime


class AuctionCreate(BaseModel):
    lot_id: int
    start_time: datetime
    end_time: datetime


class AuctionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lot_id: int
    start_time: datetime
    end_time: datetime | None
    status: AuctionStatus
    current_price: Decimal


class BidCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class BidRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    auction_id: int
    buyer_id: int
    amount: Decimal
    created_at: datetime
