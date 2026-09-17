from __future__ import annotations

import math
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.auth import (
    create_access_token,
    get_current_user_from_cookie,
    hash_password,
    password_needs_upgrade,
    verify_password,
)
from app.config import get_settings
from app.db import Base, get_db, get_engine
from app.models import Auction, AuctionStatus, Bid, Lot, User, UserRole
from app.routers import auctions as auctions_router
from app.routers import lots as lots_router
from app.routers import sales as reports_router
from app.routers import users as users_router
from app.schemas import AuctionCreate, BidCreate, LotCreate
from app.services import (
    as_money,
    close_auction,
    create_auction,
    create_lot,
    highest_bid,
    minimum_bid_for_auction,
    place_bid,
    synchronize_auction_statuses,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=get_engine())
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(users_router.router)
app.include_router(lots_router.router)
app.include_router(auctions_router.router)
app.include_router(reports_router.router)


def format_money(value) -> str:
    if value is None:
        return "0,00"
    amount = Decimal(str(value)).quantize(Decimal("0.01"))
    return f"{amount:,.2f}".replace(",", " ").replace(".", ",")


def format_datetime(value: datetime | None) -> str:
    if value is None:
        return "Без срока"
    return value.strftime("%d.%m.%Y %H:%M")


templates.env.filters["money"] = format_money
templates.env.filters["dt"] = format_datetime


def template_context(request: Request, current_user: User | None = None, **extra):
    return {
        "request": request,
        "current_user": current_user,
        "message": request.query_params.get("message"),
        "message_level": request.query_params.get("level", "info"),
        "app_name": settings.app_name,
        **extra,
    }


def redirect_with_message(url: str, message: str, level: str = "success") -> RedirectResponse:
    separator = "&" if "?" in url else "?"
    return RedirectResponse(
        url=f"{url}{separator}{urlencode({'message': message, 'level': level})}",
        status_code=303,
    )


def login_redirect(next_url: str = "/dashboard") -> RedirectResponse:
    return RedirectResponse(url=f"/login?{urlencode({'next': next_url})}", status_code=303)


def safe_next_url(value: str | None) -> str:
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return "/dashboard"


@app.exception_handler(HTTPException)
async def pretty_http_error(request: Request, exc: HTTPException):
    accepts_html = "text/html" in request.headers.get("accept", "")
    if accepts_html and not request.url.path.startswith("/api/"):
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            status_code=exc.status_code,
            context=template_context(
                request,
                error_code=exc.status_code,
                error_message=str(exc.detail),
            ),
        )
    return await http_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def pretty_validation_error(request: Request, exc: RequestValidationError):
    accepts_html = "text/html" in request.headers.get("accept", "")
    if accepts_html and not request.url.path.startswith("/api/"):
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            status_code=422,
            context=template_context(
                request,
                error_code=422,
                error_message="Проверьте заполнение формы: одно или несколько значений имеют неверный формат.",
            ),
        )
    return await request_validation_exception_handler(request, exc)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "mariadb/mysql"}


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    page: int = Query(default=1, ge=1),
    q: str = Query(default="", max_length=100),
    status_filter: str = Query(default="active", alias="status"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_from_cookie),
):
    synchronize_auction_statuses(db)

    allowed_statuses = {"active", "pending", "closed", "all"}
    if status_filter not in allowed_statuses:
        status_filter = "active"

    query = (
        db.query(Auction)
        .join(Auction.lot)
        .join(Lot.seller)
        .options(joinedload(Auction.lot).joinedload(Lot.seller))
    )

    clean_q = q.strip()
    if clean_q:
        pattern = f"%{clean_q}%"
        query = query.filter(
            or_(
                Lot.title.ilike(pattern),
                Lot.description.ilike(pattern),
                User.username.ilike(pattern),
            )
        )
    if status_filter != "all":
        query = query.filter(Auction.status == AuctionStatus(status_filter))

    if status_filter == "active":
        query = query.order_by(Auction.end_time.is_(None), Auction.end_time.asc(), Auction.id.desc())
    else:
        query = query.order_by(Auction.start_time.desc(), Auction.id.desc())

    total = query.count()
    page_size = max(1, min(settings.catalog_page_size, 30))
    total_pages = max(1, math.ceil(total / page_size))
    if page > total_pages:
        params = {"page": total_pages, "status": status_filter}
        if clean_q:
            params["q"] = clean_q
        return RedirectResponse(url=f"/?{urlencode(params)}", status_code=303)

    auctions = query.offset((page - 1) * page_size).limit(page_size).all()

    active_count = db.scalar(
        select(func.count(Auction.id)).where(Auction.status == AuctionStatus.ACTIVE)
    ) or 0
    seller_count = db.scalar(
        select(func.count(User.id)).where(User.role.in_([UserRole.SELLER, UserRole.ADMIN]))
    ) or 0
    bids_count = db.scalar(select(func.count(Bid.id))) or 0

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=template_context(
            request,
            current_user,
            auctions=auctions,
            q=clean_q,
            status_filter=status_filter,
            page=page,
            total=total,
            total_pages=total_pages,
            active_count=active_count,
            seller_count=seller_count,
            bids_count=bids_count,
        ),
    )


@app.get("/register", response_class=HTMLResponse)
def register_page(
    request: Request,
    current_user: User | None = Depends(get_current_user_from_cookie),
):
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context=template_context(request),
    )


@app.post("/register", response_class=HTMLResponse)
def register_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
):
    username = username.strip()
    email = email.strip().lower()
    form_data = {"username": username, "email": email, "role": role}

    if len(username) < 3 or len(username) > 50:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            status_code=400,
            context=template_context(request, error="Логин должен содержать от 3 до 50 символов", form_data=form_data),
        )
    if len(password) < 6:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            status_code=400,
            context=template_context(request, error="Пароль должен содержать минимум 6 символов", form_data=form_data),
        )
    if role not in {UserRole.BUYER.value, UserRole.SELLER.value}:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            status_code=400,
            context=template_context(request, error="Некорректная роль", form_data=form_data),
        )

    existing = db.scalar(
        select(User).where(or_(User.username == username, User.email == email))
    )
    if existing:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            status_code=409,
            context=template_context(request, error="Пользователь с таким логином или email уже существует", form_data=form_data),
        )

    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        role=UserRole(role),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            status_code=409,
            context=template_context(request, error="Пользователь с таким логином или email уже существует", form_data=form_data),
        )

    return redirect_with_message("/login", "Аккаунт создан. Теперь войдите в систему.")


@app.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    next: str = Query(default="/dashboard"),
    current_user: User | None = Depends(get_current_user_from_cookie),
):
    if current_user:
        return RedirectResponse(url=safe_next_url(next), status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context=template_context(request, next_url=safe_next_url(next)),
    )


@app.post("/login", response_class=HTMLResponse)
def login_user(
    request: Request,
    identity: str = Form(...),
    password: str = Form(...),
    next: str = Form(default="/dashboard"),
    db: Session = Depends(get_db),
):
    identity = identity.strip()
    user = db.scalar(
        select(User).where(or_(User.username == identity, User.email == identity.lower()))
    )
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            status_code=400,
            context=template_context(
                request,
                error="Неверный логин/email или пароль",
                identity=identity,
                next_url=safe_next_url(next),
            ),
        )

    if password_needs_upgrade(user.hashed_password):
        user.hashed_password = hash_password(password)
        db.commit()

    token = create_access_token(user)
    response = RedirectResponse(url=safe_next_url(next), status_code=303)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token", path="/")
    return response


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_from_cookie),
):
    if not current_user:
        return login_redirect("/dashboard")

    synchronize_auction_statuses(db)

    seller_rows = []
    if current_user.role in {UserRole.SELLER, UserRole.ADMIN}:
        lots = (
            db.query(Lot)
            .options(joinedload(Lot.auctions))
            .filter(Lot.seller_id == current_user.id)
            .order_by(Lot.created_at.desc())
            .all()
        )
        seller_rows = [
            {"lot": lot, "auction": lot.auctions[0] if lot.auctions else None}
            for lot in lots
        ]

    buyer_bids = []
    if current_user.role in {UserRole.BUYER, UserRole.ADMIN}:
        buyer_bids = (
            db.query(Bid)
            .options(joinedload(Bid.auction).joinedload(Auction.lot))
            .filter(Bid.buyer_id == current_user.id)
            .order_by(Bid.created_at.desc())
            .limit(25)
            .all()
        )

    available_auctions = (
        db.query(Auction)
        .options(joinedload(Auction.lot).joinedload(Lot.seller))
        .filter(Auction.status == AuctionStatus.ACTIVE)
        .order_by(Auction.end_time.is_(None), Auction.end_time.asc())
        .limit(6)
        .all()
    )
    if current_user.role == UserRole.BUYER:
        available_auctions = [a for a in available_auctions if a.lot.seller_id != current_user.id]

    won_count = 0
    if current_user.role in {UserRole.BUYER, UserRole.ADMIN}:
        closed_auctions = db.scalars(
            select(Auction).where(Auction.status == AuctionStatus.CLOSED)
        ).all()
        won_count = sum(
            1
            for auction in closed_auctions
            if (winner := highest_bid(db, auction.id)) is not None and winner.buyer_id == current_user.id
        )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=template_context(
            request,
            current_user,
            seller_rows=seller_rows,
            buyer_bids=buyer_bids,
            available_auctions=available_auctions,
            won_count=won_count,
        ),
    )


@app.get("/lots/new", response_class=HTMLResponse)
def new_lot_page(
    request: Request,
    current_user: User | None = Depends(get_current_user_from_cookie),
):
    if not current_user:
        return login_redirect("/lots/new")
    if current_user.role not in {UserRole.SELLER, UserRole.ADMIN}:
        raise HTTPException(status_code=403, detail="Создавать лоты может только продавец")
    return templates.TemplateResponse(
        request=request,
        name="lot_form.html",
        context=template_context(request, current_user),
    )


@app.post("/lots/create")
def create_lot_web(
    title: str = Form(...),
    description: str = Form(default=""),
    start_price: Decimal = Form(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_from_cookie),
):
    if not current_user:
        return login_redirect("/lots/new")
    try:
        lot = create_lot(
            db,
            current_user,
            LotCreate(title=title, description=description, start_price=start_price),
        )
    except HTTPException as exc:
        return redirect_with_message("/lots/new", str(exc.detail), "error")
    return redirect_with_message(
        f"/auctions/new?lot_id={lot.id}",
        "Лот сохранён. Теперь настройте аукцион.",
    )


@app.get("/auctions/new", response_class=HTMLResponse)
def new_auction_page(
    request: Request,
    lot_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_from_cookie),
):
    if not current_user:
        return login_redirect("/auctions/new")
    if current_user.role not in {UserRole.SELLER, UserRole.ADMIN}:
        raise HTTPException(status_code=403, detail="Создавать аукционы может только продавец")

    lots = (
        db.query(Lot)
        .options(joinedload(Lot.auctions))
        .filter(Lot.seller_id == current_user.id)
        .order_by(Lot.created_at.desc())
        .all()
    )
    eligible_lots = [
        lot
        for lot in lots
        if not any(a.status in {AuctionStatus.PENDING, AuctionStatus.ACTIVE} for a in lot.auctions)
    ]
    default_start = datetime.now().replace(second=0, microsecond=0)
    default_end = default_start + timedelta(days=1)
    return templates.TemplateResponse(
        request=request,
        name="auction_form.html",
        context=template_context(
            request,
            current_user,
            lots=eligible_lots,
            selected_lot_id=lot_id,
            default_start=default_start.strftime("%Y-%m-%dT%H:%M"),
            default_end=default_end.strftime("%Y-%m-%dT%H:%M"),
        ),
    )


@app.post("/auctions/create")
def create_auction_web(
    lot_id: int = Form(...),
    start_time: datetime = Form(...),
    end_time: datetime = Form(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_from_cookie),
):
    if not current_user:
        return login_redirect("/auctions/new")
    try:
        auction = create_auction(
            db,
            current_user,
            AuctionCreate(lot_id=lot_id, start_time=start_time, end_time=end_time),
        )
    except HTTPException as exc:
        return redirect_with_message(
            f"/auctions/new?lot_id={lot_id}", str(exc.detail), "error"
        )
    return redirect_with_message(
        f"/auctions/{auction.id}", "Аукцион создан и опубликован."
    )


@app.get("/auctions/{auction_id}", response_class=HTMLResponse)
def auction_detail(
    auction_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_from_cookie),
):
    synchronize_auction_statuses(db)
    auction = (
        db.query(Auction)
        .options(
            joinedload(Auction.lot).joinedload(Lot.seller),
            joinedload(Auction.bids).joinedload(Bid.buyer),
        )
        .filter(Auction.id == auction_id)
        .first()
    )
    if not auction:
        raise HTTPException(status_code=404, detail="Аукцион не найден")
    bids = sorted(auction.bids, key=lambda bid: (Decimal(str(bid.amount)), -bid.id), reverse=True)
    winner = highest_bid(db, auction.id) if auction.status == AuctionStatus.CLOSED else None
    minimum_bid = minimum_bid_for_auction(db, auction)
    can_bid = (
        current_user is not None
        and current_user.role in {UserRole.BUYER, UserRole.ADMIN}
        and current_user.id != auction.lot.seller_id
        and auction.status == AuctionStatus.ACTIVE
    )
    can_manage = (
        current_user is not None
        and (current_user.id == auction.lot.seller_id or current_user.role == UserRole.ADMIN)
    )
    return templates.TemplateResponse(
        request=request,
        name="auction_detail.html",
        context=template_context(
            request,
            current_user,
            auction=auction,
            bids=bids,
            winner=winner,
            minimum_bid=minimum_bid,
            can_bid=can_bid,
            can_manage=can_manage,
        ),
    )


@app.post("/auctions/{auction_id}/bid")
def place_bid_web(
    auction_id: int,
    amount: Decimal = Form(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_from_cookie),
):
    if not current_user:
        return login_redirect(f"/auctions/{auction_id}")
    try:
        place_bid(db, current_user, auction_id, BidCreate(amount=amount))
    except HTTPException as exc:
        return redirect_with_message(
            f"/auctions/{auction_id}", str(exc.detail), "error"
        )
    return redirect_with_message(f"/auctions/{auction_id}", "Ставка принята.")


@app.post("/auctions/{auction_id}/close")
def close_auction_web(
    auction_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_from_cookie),
):
    if not current_user:
        return login_redirect(f"/auctions/{auction_id}")
    try:
        close_auction(db, current_user, auction_id)
    except HTTPException as exc:
        return redirect_with_message(
            f"/auctions/{auction_id}", str(exc.detail), "error"
        )
    return redirect_with_message(f"/auctions/{auction_id}", "Аукцион завершён.")


@app.get("/lots/{lot_id}/bids")
def old_lot_bids_route(lot_id: int, db: Session = Depends(get_db)):
    auction = db.scalar(
        select(Auction)
        .where(Auction.lot_id == lot_id)
        .order_by(Auction.start_time.desc(), Auction.id.desc())
        .limit(1)
    )
    if not auction:
        return RedirectResponse(url="/", status_code=303)
    return RedirectResponse(url=f"/auctions/{auction.id}", status_code=303)
