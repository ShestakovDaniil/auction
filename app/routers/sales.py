from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Sale, User
from app.schemas import RevenueRow, SaleRead

router = APIRouter(prefix="/api", tags=["sales & reports"])


@router.get("/sales", response_model=list[SaleRead])
def list_sales(db: Session = Depends(get_db)):
    return db.scalars(select(Sale).order_by(Sale.sold_at.desc())).all()


@router.get("/reports/revenue", response_model=list[RevenueRow])
def revenue_report(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = (
        select(
            Sale.seller_id,
            User.name.label("seller_name"),
            func.count(Sale.id).label("sales_count"),
            func.coalesce(func.sum(Sale.final_price), 0).label("revenue"),
        )
        .join(User, User.id == Sale.seller_id)
        .group_by(Sale.seller_id, User.name)
        .order_by(func.sum(Sale.final_price).desc())
    )
    if date_from is not None:
        stmt = stmt.where(Sale.sold_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Sale.sold_at <= date_to)

    rows = db.execute(stmt).all()
    return [
        RevenueRow(
            seller_id=row.seller_id,
            seller_name=row.seller_name,
            sales_count=row.sales_count,
            revenue=Decimal(row.revenue),
        )
        for row in rows
    ]
