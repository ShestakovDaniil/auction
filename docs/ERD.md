# ERD

```mermaid
erDiagram
    USERS ||--o{ LOTS : sells
    LOTS ||--o{ AUCTIONS : listed_as
    USERS ||--o{ SALES : bids
    AUCTIONS ||--o{ SALES : receives

    USERS {
        int id PK
        varchar username UK
        varchar email UK
        varchar hashed_password
        enum role
        datetime created_at
    }
    LOTS {
        int id PK
        varchar title
        text description
        decimal start_price
        int seller_id FK
        enum status
        datetime created_at
    }
    AUCTIONS {
        int id PK
        int lot_id FK
        datetime start_time
        datetime end_time
        enum status
        decimal current_price
    }
    SALES {
        int id PK
        int auction_id FK
        int buyer_id FK
        decimal amount
        datetime created_at
    }
```

## Связи

- один пользователь-продавец может создать несколько лотов;
- один лот может иметь несколько аукционов последовательно;
- один аукцион принимает несколько ставок;
- одна ставка принадлежит одному покупателю и одному аукциону.

## Изменения лабораторной работы №3

- `lots.condition VARCHAR(16) NOT NULL DEFAULT 'used'` (миграция `0002`). Для старых лотов
  состояние устанавливается автоматически.
- `favorite_lots` (миграция `0003`): `id` (PK), `user_id` (FK → users.id, CASCADE),
  `lot_id` (FK → lots.id, CASCADE), `created_at`. Пара `(user_id, lot_id)` уникальна.
- Связи: User 1:N FavoriteLot N:1 Lot. Отображается только избранное текущего пользователя.
