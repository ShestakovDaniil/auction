# HTTP API

После запуска интерактивная документация доступна по адресу `http://127.0.0.1:8000/docs`.

## Основные адреса

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/health` | Проверка приложения и подключения к БД |
| GET | `/api/users` | Список пользователей |
| POST | `/api/users` | Создать покупателя/продавца |
| GET | `/api/auctions` | Список аукционов |
| POST | `/api/auctions` | Создать аукцион |
| GET | `/api/auctions/{id}` | Получить аукцион |
| GET | `/api/auctions/{id}/lots` | Лоты аукциона |
| POST | `/api/auctions/{id}/lots` | Добавить лот |
| GET | `/api/lots/{id}` | Получить лот |
| GET | `/api/lots/{id}/bids` | Ставки по лоту |
| POST | `/api/lots/{id}/bids` | Сделать ставку |
| POST | `/api/lots/{id}/close` | Закрыть лот после окончания аукциона |
| GET | `/api/sales` | Продажи |
| GET | `/api/reports/revenue` | Доходы продавцов; можно передать `date_from` и `date_to` |

## Примеры

Создать пользователя:

```bash
curl -X POST http://127.0.0.1:8000/api/users \
  -H 'Content-Type: application/json' \
  -d '{"name":"Иван","email":"ivan@example.com","role":"buyer"}'
```

Сделать ставку:

```bash
curl -X POST http://127.0.0.1:8000/api/lots/1/bids \
  -H 'Content-Type: application/json' \
  -d '{"buyer_id":2,"amount":2600.00}'
```

Некорректные запросы получают HTTP-коды `404`, `409` или `422` с полем `detail`.
