from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.auth import hash_password
from app.db import Base, SessionLocal, get_engine
from app.models import Auction, AuctionStatus, Bid, Lot, LotStatus, User, UserRole


def main() -> None:
    Base.metadata.create_all(bind=get_engine())
    with SessionLocal(bind=get_engine()) as db:
        if db.scalar(select(User.id).limit(1)) is not None:
            print("Seed skipped: database already contains users.")
            return

        seller = User(
            username="seller_demo",
            email="seller@example.com",
            hashed_password=hash_password("seller123"),
            role=UserRole.SELLER,
        )
        buyer = User(
            username="buyer_demo",
            email="buyer@example.com",
            hashed_password=hash_password("buyer123"),
            role=UserRole.BUYER,
        )
        db.add_all([seller, buyer])
        db.flush()

        lot1 = Lot(
            title="Механическая клавиатура",
            description="Демонстрационный лот: клавиатура в отличном состоянии.",
            start_price=Decimal("2500.00"),
            seller_id=seller.id,
            status=LotStatus.ACTIVE,
        )
        lot2 = Lot(
            title="Монитор 27 дюймов",
            description="IPS-монитор, демонстрационные данные для лабораторной работы.",
            start_price=Decimal("12000.00"),
            seller_id=seller.id,
            status=LotStatus.ACTIVE,
        )
        db.add_all([lot1, lot2])
        db.flush()

        now = datetime.now()
        auction1 = Auction(
            lot_id=lot1.id,
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(days=2),
            status=AuctionStatus.ACTIVE,
            current_price=Decimal("2700.00"),
        )
        auction2 = Auction(
            lot_id=lot2.id,
            start_time=now + timedelta(hours=2),
            end_time=now + timedelta(days=3),
            status=AuctionStatus.PENDING,
            current_price=Decimal("12000.00"),
        )
        db.add_all([auction1, auction2])
        db.flush()

        db.add(
            Bid(
                auction_id=auction1.id,
                buyer_id=buyer.id,
                amount=Decimal("2700.00"),
            )
        )
        db.commit()

    print("Demo data created.")
    print("Seller: seller_demo / seller123")
    print("Buyer:  buyer_demo / buyer123")


if __name__ == "__main__":
    main()
