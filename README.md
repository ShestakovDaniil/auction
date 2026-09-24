# Auction Lab

## Возможности

- регистрация покупателей и продавцов;
- вход по логину или email;
- личный кабинет с данными пользователя, его лотами и ставками;
- создание лотов продавцом;
- запуск аукциона для собственного лота;
- просмотр активных, ожидающих и завершённых аукционов;
- поиск и фильтрация каталога;
- проведение ставок покупателями;
- контроль минимальной следующей ставки;
- блокировка ставки продавца на собственный лот;
- завершение аукциона владельцем или администратором;
- вычисление победителя по максимальной ставке;
- JSON API и Swagger UI;
- проверка подключения к MariaDB/MySQL через `/health` и `scripts/check_db.py`.

## Технологии

- Python 3.11+
- FastAPI
- SQLAlchemy 2
- MariaDB / MySQL
- PyMySQL
- Pydantic v2
- Jinja2
- Uvicorn

## Модель данных

В системе используются четыре таблицы:

- `users` – пользователи, их учетные данные и роли;
- `lots` – лоты продавцов;
- `auctions` – аукционы, связанные с лотами;
- `sales` – журнал ставок. Историческое имя таблицы сохранено для совместимости, в коде сущность называется `Bid`.

Подробная схема приведена в [`docs/ERD.md`](docs/ERD.md).

## Роли

### Покупатель (`buyer`)

Может просматривать аукционы после авторизации, делать ставки, видеть свои ставки и результаты участия.

### Продавец (`seller`)

Может создавать собственные лоты, запускать по ним аукционы и завершать свои аукционы.

### Администратор (`admin`)

Служебная роль с расширенными полномочиями. Администратор может завершать аукционы и получать сводный отчёт API. Публичная регистрация администратора запрещена.

## Структура проекта

```text
.
├── app
│   ├── __init__.py
│   ├── access.py
│   ├── auth.py
│   ├── config.py
│   ├── db.py
│   ├── domain.py
│   ├── http.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── security.py
│   ├── services.py
│   ├── routers
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── index.py
│   │   ├── register.py
│   │   ├── login.py
│   │   ├── logout.py
│   │   ├── dashboard.py
│   │   ├── lot_new.py
│   │   ├── lot_create.py
│   │   ├── auction_new.py
│   │   ├── auction_create.py
│   │   ├── auction_detail.py
│   │   ├── auction_bid.py
│   │   ├── auction_close.py
│   │   ├── api_user_create.py
│   │   ├── api_user_me.py
│   │   ├── api_lot_create.py
│   │   ├── api_lot_get.py
│   │   ├── api_lot_bids.py
│   │   ├── api_auction_list.py
│   │   ├── api_auction_get.py
│   │   ├── api_auction_create.py
│   │   ├── api_auction_close.py
│   │   ├── api_bid_create.py
│   │   └── api_report_summary.py
│   ├── static
│   │   └── styles.css
│   └── templates
│       ├── auction_detail.html
│       ├── auction_form.html
│       ├── base.html
│       ├── dashboard.html
│       ├── error.html
│       ├── index.html
│       ├── login.html
│       ├── lot_form.html
│       └── register.html
├── docs
│   ├── API.md
│   └── ERD.md
├── scripts
│   ├── check_db.py
│   └── setup_env.py
├── .gitignore
├── README.md
├── TZ_ANALYSIS.md
└── requirements.txt
```

## Назначение всех файлов

### Корень проекта

- `.gitignore` – исключает локальный `.env`, виртуальные окружения, кэш Python и файлы IDE из Git.
- `requirements.txt` – зависимости Python, необходимые для запуска приложения.

### `app/`

- `app/__init__.py` – обозначает каталог `app` как Python-пакет.
- `app/main.py` – создаёт FastAPI-приложение, подключает роутеры, статику, middleware безопасности и обработчики ошибок.
- `app/config.py` – загружает настройки из `.env`, проверяет тип СУБД, секрет приложения и production-параметры.
- `app/db.py` – создаёт SQLAlchemy engine и сессии MariaDB/MySQL.
- `app/models.py` – содержит ORM-модели `User`, `Lot`, `Auction`, `Bid`, enum-статусы и ограничения таблиц.
- `app/schemas.py` – Pydantic-схемы входных и выходных данных API.
- `app/auth.py` – хэширование и проверка паролей, выпуск и проверка JWT, получение текущего пользователя и проверка ролей.
- `app/access.py` – объектная авторизация: проверка видимости и владения лотами/аукционами и доступа к истории ставок.
- `app/security.py` – CSRF-защита, безопасный локальный redirect и ограничение частых попыток входа.
- `app/http.py` – общие Jinja-шаблоны, фильтры форматирования, контекст страниц и redirect с сообщением.
- `app/services.py` – бизнес-операции: создание пользователей/лотов/аукционов, ставки, завершение и синхронизация статусов.
- `app/domain.py` – изолированные правила предметной области для вычисления минимальной ставки и проверки временного окна.

### `app/routers/`

- `app/routers/__init__.py` – единый список роутеров, подключаемых в `app/main.py`.
- `app/routers/health.py` – `GET /health`.
- `app/routers/index.py` – `GET /`, каталог аукционов.
- `app/routers/register.py` – `GET /register`, `POST /register`.
- `app/routers/login.py` – `GET /login`, `POST /login`.
- `app/routers/logout.py` – `POST /logout`.
- `app/routers/dashboard.py` – `GET /dashboard`.
- `app/routers/lot_new.py` – `GET /lots/new`.
- `app/routers/lot_create.py` – `POST /lots/create`.
- `app/routers/auction_new.py` – `GET /auctions/new`.
- `app/routers/auction_create.py` – `POST /auctions/create`.
- `app/routers/auction_detail.py` – `GET /auctions/{auction_id}`.
- `app/routers/auction_bid.py` – `POST /auctions/{auction_id}/bid`.
- `app/routers/auction_close.py` – `POST /auctions/{auction_id}/close`.
- `app/routers/api_user_create.py` – `POST /api/users`.
- `app/routers/api_user_me.py` – `GET /api/users/me`.
- `app/routers/api_lot_create.py` – `POST /api/lots`.
- `app/routers/api_lot_get.py` – `GET /api/lots/{lot_id}`.
- `app/routers/api_lot_bids.py` – `GET /api/lots/{lot_id}/bids`.
- `app/routers/api_auction_list.py` – `GET /api/auctions`.
- `app/routers/api_auction_get.py` – `GET /api/auctions/{auction_id}`.
- `app/routers/api_auction_create.py` – `POST /api/auctions`.
- `app/routers/api_auction_close.py` – `POST /api/auctions/{auction_id}/close`.
- `app/routers/api_bid_create.py` – `POST /api/auctions/{auction_id}/bids`.
- `app/routers/api_report_summary.py` – `GET /api/reports/summary`.

### `app/templates/`

- `base.html` – базовая HTML-разметка, навигация, сообщения и footer.
- `index.html` – каталог аукционов с фильтрами, поиском и пагинацией.
- `login.html` – форма входа.
- `register.html` – форма регистрации и выбора роли.
- `dashboard.html` – личный кабинет покупателя/продавца.
- `lot_form.html` – создание лота.
- `auction_form.html` – запуск аукциона для собственного лота.
- `auction_detail.html` – карточка аукциона, история ставок, ставка и управление завершением.
- `error.html` – отображение HTML-ошибок приложения.

### `app/static/`

- `styles.css` – стили всего веб-интерфейса.

### `docs/`

- `docs/API.md` – компактная спецификация HTTP API и требований авторизации.
- `docs/ERD.md` – ER-диаграмма и описание связей таблиц.

### `scripts/`

- `scripts/check_db.py` – проверяет соединение с MariaDB/MySQL и выводит версию сервера.
- `scripts/setup_env.py` – интерактивно создаёт локальный `.env`, запрашивает параметры MariaDB/MySQL и генерирует `APP_SECRET_KEY`.

## HTTP-маршруты

### Веб-интерфейс

| Метод | URL | Доступ | Назначение |
|---|---|---|---|
| `GET` | `/` | авторизованный пользователь | Каталог аукционов, поиск, фильтры и пагинация |
| `GET` | `/register` | публичный | Страница регистрации |
| `POST` | `/register` | публичный | Создание покупателя или продавца |
| `GET` | `/login` | публичный | Страница входа |
| `POST` | `/login` | публичный | Аутентификация и установка auth-cookie |
| `POST` | `/logout` | авторизованный | Завершение браузерной сессии |
| `GET` | `/dashboard` | авторизованный | Личный кабинет |
| `GET` | `/lots/new` | продавец / admin | Форма нового лота |
| `POST` | `/lots/create` | продавец / admin | Создание лота |
| `GET` | `/auctions/new` | продавец / admin | Форма запуска аукциона |
| `POST` | `/auctions/create` | владелец лота / admin | Создание аукциона |
| `GET` | `/auctions/{auction_id}` | авторизованный | Просмотр конкретного аукциона |
| `POST` | `/auctions/{auction_id}/bid` | покупатель / admin | Создание ставки |
| `POST` | `/auctions/{auction_id}/close` | владелец / admin | Завершение аукциона |
| `GET` | `/health` | публичный | Проверка доступности приложения и БД |

### JSON API

| Метод | URL | Доступ | Назначение |
|---|---|---|---|
| `POST` | `/api/users` | публичный | Регистрация покупателя или продавца |
| `GET` | `/api/users/me` | авторизованный | Данные текущего пользователя |
| `POST` | `/api/lots` | продавец / admin | Создание лота |
| `GET` | `/api/lots/{lot_id}` | авторизованный, с проверкой доступа | Получение лота |
| `GET` | `/api/lots/{lot_id}/bids` | владелец / admin / участник | История ставок лота |
| `GET` | `/api/auctions` | авторизованный | Список аукционов |
| `GET` | `/api/auctions/{auction_id}` | авторизованный | Получение аукциона |
| `POST` | `/api/auctions` | владелец лота / admin | Создание аукциона |
| `POST` | `/api/auctions/{auction_id}/close` | владелец / admin | Завершение аукциона |
| `POST` | `/api/auctions/{auction_id}/bids` | покупатель / admin | Создание ставки |
| `GET` | `/api/reports/summary` | admin | Сводные счётчики пользователей, лотов, аукционов и ставок |

Служебные маршруты FastAPI: `/docs`, `/redoc`, `/openapi.json`.

## Бизнес-правила

- лот создаётся в статусе `draft`;
- создавать лоты может продавец или администратор;
- аукцион создаётся только для собственного лота, кроме операций администратора;
- одновременно у лота не может быть двух активных/ожидающих аукционов;
- окончание аукциона должно быть позже начала и позже текущего времени;
- первая ставка может быть равна стартовой цене;
- каждая следующая ставка должна быть не ниже текущей цены плюс `MIN_BID_INCREMENT`;
- продавец не может делать ставку на собственный лот;
- при одновременных ставках строка аукциона блокируется через `SELECT ... FOR UPDATE`;
- завершённый аукцион больше не принимает ставки;
- победителем считается максимальная ставка; при равенстве учитывается более ранняя ставка.

## Подготовка MariaDB / MySQL

Перед первым запуском создайте базу данных и отдельного пользователя приложения.

Пример для MariaDB / MySQL:

```sql
CREATE DATABASE auction_lab
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER 'auction_app'@'127.0.0.1'
    IDENTIFIED BY 'change_me';

GRANT ALL PRIVILEGES ON auction_lab.*
    TO 'auction_app'@'127.0.0.1';

FLUSH PRIVILEGES;
```

Значения `auction_app`, `change_me` и `auction_lab` можно заменить на собственные. Эти же параметры потребуются при настройке приложения.

## Установка

Клонируйте репозиторий и перейдите в каталог проекта:

```bash
git clone --branch develop --single-branch https://github.com/ShestakovDaniil/auction.git
cd auction
```

Создайте виртуальное окружение:

```bash
python3 -m venv .venv
```

Активируйте его.

Linux / macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Установите зависимости:

```bash
python -m pip install -r requirements.txt
```

## Конфигурация

Создайте локальную конфигурацию приложения:

```bash
python -m scripts.setup_env
```

Скрипт автоматически создаст файл `.env` в корне проекта, сгенерирует безопасный `APP_SECRET_KEY` и заполнит остальные параметры значениями по умолчанию.

Во время настройки потребуется указать только параметры подключения к MariaDB / MySQL:

- пользователь БД – по умолчанию `auction_app`;
- пароль пользователя БД;
- хост – по умолчанию `127.0.0.1`;
- порт – по умолчанию `3306`;
- имя базы данных – по умолчанию `auction_lab`.

Если оставить значение пустым и нажать Enter, будет использовано значение по умолчанию.

Пример:

```text
Настройка Auction Lab

Пользователь MariaDB [auction_app]:
Пароль MariaDB: ********
Хост MariaDB [127.0.0.1]:
Порт MariaDB [3306]:
Название базы [auction_lab]:

.env создан.
APP_SECRET_KEY сгенерирован автоматически.
```

Файл `.env` содержит секретные данные и не должен попадать в Git. Он исключён через `.gitignore`.

## Проверка подключения к БД

После создания `.env` проверьте соединение с MariaDB / MySQL:

```bash
python -m scripts.check_db
```

При успешном подключении будет выведена версия сервера MariaDB / MySQL.

Если подключение не удалось, проверьте логин, пароль, имя базы данных, адрес сервера и права пользователя БД.

## Запуск

Запустите приложение из корня проекта:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

После запуска доступны:

- приложение: `http://127.0.0.1:8000/`;
- Swagger UI: `http://127.0.0.1:8000/docs`;
- OpenAPI: `http://127.0.0.1:8000/openapi.json`;
- health-check: `http://127.0.0.1:8000/health`.

Для остановки сервера используйте `Ctrl+C`.

При повторном запуске проекта достаточно активировать виртуальное окружение и запустить Uvicorn повторно:

Linux / macOS:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
