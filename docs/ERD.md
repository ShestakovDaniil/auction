# Схема данных

```mermaid
erDiagram
    USERS ||--o{ AUCTIONS : organizes
    USERS ||--o{ LOTS : sells
    AUCTIONS ||--o{ LOTS : contains
    USERS ||--o{ BIDS : makes
    LOTS ||--o{ BIDS : receives
    LOTS ||--o| SALES : closes_as
    USERS ||--o{ SALES : buys
    USERS ||--o{ SALES : sells

    USERS {
        bigint id PK
        varchar name
        varchar email UK
        enum role
        datetime created_at
    }
    AUCTIONS {
        bigint id PK
        varchar title
        text description
        datetime starts_at
        datetime ends_at
        bigint organizer_id FK
    }
    LOTS {
        bigint id PK
        bigint auction_id FK
        bigint seller_id FK
        varchar title
        decimal start_price
        decimal min_increment
        enum status
    }
    BIDS {
        bigint id PK
        bigint lot_id FK
        bigint buyer_id FK
        decimal amount
        datetime created_at
    }
    SALES {
        bigint id PK
        bigint lot_id FK_UK
        bigint buyer_id FK
        bigint seller_id FK
        decimal final_price
        datetime sold_at
    }
```

## Связи

- Один пользователь-продавец может организовать много аукционов.
- Один аукцион содержит много лотов.
- Каждый лот имеет одного продавца и много ставок.
- Покупатель может сделать много ставок на разные лоты.
- Закрытый с победителем лот имеет ровно одну запись продажи.
