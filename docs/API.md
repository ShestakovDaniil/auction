# HTTP API

Интерактивная документация доступна после запуска приложения по адресу `/docs`.

Все API-маршруты, кроме `POST /api/users`, требуют действующую `HttpOnly` auth-cookie `access_token`.
Изменяющие авторизованные запросы дополнительно требуют заголовок `X-CSRF-Token` со значением cookie `csrf_token`.

| Метод | URL | Доступ | Назначение |
|---|---|---|---|
| GET | `/health` | публичный | Проверка приложения и соединения с БД |
| POST | `/api/users` | публичный | Регистрация buyer/seller |
| GET | `/api/users/me` | авторизованный | Текущий пользователь |
| POST | `/api/lots` | seller/admin | Создать лот |
| GET | `/api/lots/{lot_id}` | авторизованный | Получить доступный пользователю лот |
| GET | `/api/lots/{lot_id}/bids` | owner/admin/participant | История ставок лота |
| GET | `/api/auctions` | авторизованный | Список аукционов |
| GET | `/api/auctions/{auction_id}` | авторизованный | Получить аукцион |
| POST | `/api/auctions` | owner/admin | Создать аукцион для собственного лота |
| POST | `/api/auctions/{auction_id}/close` | owner/admin | Завершить аукцион |
| POST | `/api/auctions/{auction_id}/bids` | buyer/admin | Сделать ставку |
| GET | `/api/reports/summary` | admin | Сводные счётчики системы |

Для POST API после входа передавайте:

```text
X-CSRF-Token: <значение cookie csrf_token>
```
