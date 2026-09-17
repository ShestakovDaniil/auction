# Auction Lab 1

Учебное веб-приложение по предметной области **«Аукционы»** для лабораторной работы №1 «Сквозной проект и Git-процесс».

Реализовано: FastAPI + SQLAlchemy + MariaDB/MySQL + Jinja2. Есть HTTP API, Swagger, веб-интерфейс, health-check, связанные сущности, бизнес-правила, обработка ошибок, `.env`, документация и тесты.

## Что реализовано

- сущности `User`, `Auction`, `Lot`, `Bid`, `Sale`;
- продавцы, покупатели и роль `both`;
- аукционы с периодом проведения;
- лоты со стартовой ценой и минимальным шагом;
- ставки с проверкой правил;
- закрытие лота и фиксация продажи;
- отчёт по доходам продавцов;
- веб-интерфейс `/`;
- JSON API `/api/...`;
- Swagger `/docs`;
- служебный health-check `/health`.

## Стек

- Python 3.11+
- FastAPI
- SQLAlchemy 2
- MariaDB / MySQL
- PyMySQL
- Jinja2
- Pytest

## 1. Создание базы MariaDB/MySQL

Войти в БД:

```bash
mariadb -u root -p
```

Выполнить:

```sql
CREATE DATABASE auction_lab
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER 'auction_app'@'127.0.0.1' IDENTIFIED BY 'change_me';
GRANT ALL PRIVILEGES ON auction_lab.* TO 'auction_app'@'127.0.0.1';
FLUSH PRIVILEGES;
```

Если сервер БД расположен не локально, измените host в `DATABASE_URL`.

## 2. Установка

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

В `.env` проверьте строку подключения:

```env
DATABASE_URL=mysql+pymysql://auction_app:change_me@127.0.0.1:3306/auction_lab?charset=utf8mb4
```

Таблицы создаются автоматически при запуске (`AUTO_CREATE_TABLES=true`).

## 3. Запуск

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Открыть:

- `http://127.0.0.1:8000/` — веб-интерфейс;
- `http://127.0.0.1:8000/docs` — Swagger/OpenAPI;
- `http://127.0.0.1:8000/health` — проверка работоспособности.

## 4. Демо-данные

После настройки `.env`:

```bash
python scripts/seed.py
```

Скрипт создаст продавца, покупателя, пользователя `both`, аукцион и два лота.

## 5. Проверки перед коммитом

```bash
python -m compileall app scripts tests
pytest -q
```

## 6. Основное правило предметной области

Ставка принимается только во время аукциона. Первая ставка должна быть не ниже стартовой цены, каждая следующая — не ниже текущей максимальной ставки плюс минимальный шаг. Продавец не может делать ставку на собственный лот.

## 7. Документы

- ТЗ: `docs/TECHNICAL_SPECIFICATION.md`
- API: `docs/API.md`
- ER-схема: `docs/ERD.md`
- Git-процесс: `docs/GIT_PROCESS.md`

## 8. Рекомендуемый Git-путь лабораторной

### Первичная публикация

```bash
git init
git branch -M main
git add .
git commit -m "chore: bootstrap auction lab project"
git remote add origin <URL_ВАШЕГО_РЕПОЗИТОРИЯ>
git push -u origin main
```

Создайте Issue, например: **«Реализовать размещение ставок с минимальным шагом»**.

### Отдельная ветка функции

```bash
git switch -c feature/bidding
```

Для демонстрации нескольких осмысленных коммитов можно разбить работу так:

```bash
git add app/domain.py tests/test_domain.py
git commit -m "feat: add bid domain validation rules"

git add app/services.py app/routers/lots.py
git commit -m "feat: implement transactional bidding API"

git add docs/API.md README.md
git commit -m "docs: document bidding workflow"

git push -u origin feature/bidding
```

Далее создайте Pull Request / Merge Request в `main`, выполните проверку и merge.

> Если вы уже загрузили готовый проект одним первым коммитом, для защиты лучше выбрать небольшую новую функцию/изменение и именно её провести через Issue → branch → commits → PR/MR.

### Демонстрация конфликта слияния

Создайте две ветки от одной версии `main` и измените в обеих одну и ту же строку README.

```bash
git switch main
git pull

git switch -c demo/conflict-a
# измените одну строку в README.md
git add README.md
git commit -m "docs: update project description variant A"

git switch main
git switch -c demo/conflict-b
# измените ТУ ЖЕ строку иначе
git add README.md
git commit -m "docs: update project description variant B"

git switch demo/conflict-a
git merge demo/conflict-b
```

Git покажет конфликт. Откройте `README.md`, удалите маркеры `<<<<<<<`, `=======`, `>>>>>>>`, оставьте итоговый текст и завершите:

```bash
git add README.md
git commit -m "merge: resolve README conflict"
```

Для наглядной защиты такую demo-ветку можно не сливать в `main`, если преподавателю нужен только факт моделирования и разрешения конфликта.

### Первая версия `v0.1.0`

После слияния всех нужных изменений:

```bash
git switch main
git pull
python -m compileall app scripts tests
pytest -q

git tag -a v0.1.0 -m "Auction Lab v0.1.0"
git push origin main
git push origin v0.1.0
```

Проверка истории на защите:

```bash
git log --graph --decorate --oneline --all
git tag -n
```

## 9. Как показать, что секреты не попали в Git

```bash
git status --ignored
git check-ignore -v .env
```

Команда должна показать, что `.env` игнорируется правилом из `.gitignore`. В репозитории хранится только безопасный шаблон `.env.example`.