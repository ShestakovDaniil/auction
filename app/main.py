from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Base, engine, get_db
from app.models import Auction, Bid, Lot, Sale, User, UserRole
from app.routers import auctions, lots, sales, users
from app.schemas import AuctionCreate, BidCreate, LotCreate, UserCreate
from app.services import create_auction, create_lot, create_user, current_price, place_bid, close_lot

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Учебная система учета аукционов, лотов, ставок, продаж и доходов.",
    lifespan=lifespan,
)

app.include_router(users.router)
app.include_router(auctions.router)
app.include_router(lots.router)
app.include_router(sales.router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


def _redirect(message: str | None = None, error: str | None = None) -> RedirectResponse:
    params = {}
    if message:
        params["message"] = message
    if error:
        params["error"] = error
    suffix = f"?{urlencode(params)}" if params else ""
    return RedirectResponse(url=f"/{suffix}", status_code=303)


def _human_error(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        return str(exc.detail)
    if isinstance(exc, ValidationError):
        first = exc.errors()[0]
        return first.get("msg", "Validation error")
    return str(exc)


@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail={"status": "error", "database": "unavailable"}) from exc
    return {"status": "ok", "database": "ok", "version": app.version}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    users_list = db.scalars(select(User).order_by(User.id)).all()
    auctions_list = db.scalars(select(Auction).order_by(Auction.starts_at.desc())).all()
    lots_list = db.scalars(select(Lot).order_by(Lot.id.desc()).limit(50)).all()
    sales_list = db.scalars(select(Sale).order_by(Sale.sold_at.desc()).limit(20)).all()

    lot_rows = []
    for lot in lots_list:
        highest = db.scalar(select(func.max(Bid.amount)).where(Bid.lot_id == lot.id))
        lot_rows.append(
            {
                "lot": lot,
                "current_price": Decimal(highest) if highest is not None else Decimal(lot.start_price),
            }
        )

    revenue_rows = db.execute(
        select(
            Sale.seller_id,
            User.name,
            func.count(Sale.id),
            func.coalesce(func.sum(Sale.final_price), 0),
        )
        .join(User, User.id == Sale.seller_id)
        .group_by(Sale.seller_id, User.name)
        .order_by(func.sum(Sale.final_price).desc())
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "users": users_list,
            "auctions": auctions_list,
            "lot_rows": lot_rows,
            "sales": sales_list,
            "revenue_rows": revenue_rows,
            "roles": [role.value for role in UserRole],
            "now": datetime.now(),
            "message": request.query_params.get("message"),
            "error": request.query_params.get("error"),
        },
    )


@app.post("/ui/users")
def ui_create_user(
    name: str = Form(...),
    email: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        create_user(db, UserCreate(name=name, email=email, role=role))
        return _redirect(message="Пользователь создан")
    except Exception as exc:
        return _redirect(error=_human_error(exc))


@app.post("/ui/auctions")
def ui_create_auction(
    title: str = Form(...),
    description: str = Form(""),
    starts_at: datetime = Form(...),
    ends_at: datetime = Form(...),
    organizer_id: int = Form(...),
    db: Session = Depends(get_db),
):
    try:
        create_auction(
            db,
            AuctionCreate(
                title=title,
                description=description or None,
                starts_at=starts_at,
                ends_at=ends_at,
                organizer_id=organizer_id,
            ),
        )
        return _redirect(message="Аукцион создан")
    except Exception as exc:
        return _redirect(error=_human_error(exc))


@app.post("/ui/lots")
def ui_create_lot(
    auction_id: int = Form(...),
    seller_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    start_price: str = Form(...),
    min_increment: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        create_lot(
            db,
            auction_id,
            LotCreate(
                seller_id=seller_id,
                title=title,
                description=description or None,
                start_price=Decimal(start_price),
                min_increment=Decimal(min_increment),
            ),
        )
        return _redirect(message="Лот создан")
    except (InvalidOperation, Exception) as exc:
        return _redirect(error=_human_error(exc))


@app.post("/ui/bids")
def ui_place_bid(
    lot_id: int = Form(...),
    buyer_id: int = Form(...),
    amount: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        place_bid(db, lot_id, BidCreate(buyer_id=buyer_id, amount=Decimal(amount)))
        return _redirect(message="Ставка принята")
    except (InvalidOperation, Exception) as exc:
        return _redirect(error=_human_error(exc))


@app.post("/ui/lots/{lot_id}/close")
def ui_close_lot(lot_id: int, db: Session = Depends(get_db)):
    try:
        sale = close_lot(db, lot_id)
        if sale:
            return _redirect(message=f"Лот закрыт. Продажа на сумму {sale.final_price}")
        return _redirect(message="Лот закрыт без продажи")
    except Exception as exc:
        return _redirect(error=_human_error(exc))
