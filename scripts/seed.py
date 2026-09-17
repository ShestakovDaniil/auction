from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import Auction, Lot, User, UserRole


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)) is not None:
            print("Seed skipped: users already exist.")
            return

        seller = User(name="Анна Продавец", email="seller@example.com", role=UserRole.SELLER)
        buyer = User(name="Иван Покупатель", email="buyer@example.com", role=UserRole.BUYER)
        both = User(name="Мария Универсал", email="both@example.com", role=UserRole.BOTH)
        db.add_all([seller, buyer, both])
        db.flush()

        now = datetime.now()
        auction = Auction(
            title="Демо-аукцион техники",
            description="Тестовые данные для защиты лабораторной работы.",
            starts_at=now - timedelta(minutes=5),
            ends_at=now + timedelta(days=7),
            organizer_id=seller.id,
        )
        db.add(auction)
        db.flush()

        db.add_all(
            [
                Lot(
                    auction_id=auction.id,
                    seller_id=seller.id,
                    title="Механическая клавиатура",
                    description="Демонстрационный лот",
                    start_price=Decimal("2500.00"),
                    min_increment=Decimal("100.00"),
                ),
                Lot(
                    auction_id=auction.id,
                    seller_id=seller.id,
                    title="Монитор 27 дюймов",
                    description="Демонстрационный лот",
                    start_price=Decimal("12000.00"),
                    min_increment=Decimal("500.00"),
                ),
            ]
        )
        db.commit()
        print("Demo data created.")


if __name__ == "__main__":
    main()
