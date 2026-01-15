# Сервис сбора событий обучения
FastAPI‑сервис для сбора событий обучения, расчёта учебных метрик и выдачи аналитики. Сырые события пишутся в ClickHouse, агрегаты и пользователи хранятся в PostgreSQL, а доступ защищён JWT (access/refresh) с ролевой моделью.

## Возможности
- JWT-аутентификация с ролями `student`/`teacher`/`admin`, refresh-токены в базе.
- Приём батчей событий через HTTP (JSONEachRow в ClickHouse).
- Расчёт метрик Retention, Engagement, Completion, Time-on-Task, Activity Index, Focus Ratio и сохранение результатов в PostgreSQL.
- Отдача метрик по пользователю и агрегатов по курсу с проверкой прав доступа.
- Uvicorn + FastAPI, SQLAlchemy, httpx; тесты на pytest.

## Быстрый старт (Docker)
1. Скопируйте `.env.example` в `.env` и при необходимости обновите значения.
2. Соберите и запустите сервисы:
   ```bash
   docker-compose up --build
   ```
3. API: `http://localhost:8000` (Swagger UI: `/docs`, OpenAPI: `/openapi.json`).
4. Стандартные подключения из compose:
   - PostgreSQL: `postgresql://app:app@localhost:5432/app`
   - ClickHouse HTTP: `http://localhost:8123`

Утилиты docker-compose:
- Остановить и удалить контейнеры (с сохранением данных): `docker-compose down`
- Полностью очистить вместе с volumes: `docker-compose down -v`

## Локальная разработка без Docker
1. Требования: Python 3.11+, запущенные PostgreSQL и ClickHouse.
2. Установите зависимости:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Создайте `.env` на основе `.env.example` и проставьте свои строки подключения.
4. Запустите API:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   Модель данных создаётся автоматически при старте (`Base.metadata.create_all`), миграции Alembic доступны при необходимости.

## Переменные окружения
- `SECRET_KEY` — ключ для подписи JWT.
- `JWT_ALGORITHM` — алгоритм (по умолчанию HS256).
- `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_MINUTES` — TTL токенов.
- `REFRESH_CLEANUP_INTERVAL_SECONDS` — период очистки просроченных refresh-токенов.
- `DATABASE_URL` — строка подключения к PostgreSQL (`postgresql+psycopg2://...`).
- `CLICKHOUSE_URL` / `CLICKHOUSE_USER` / `CLICKHOUSE_PASSWORD` / `CLICKHOUSE_DATABASE` — настройки ClickHouse HTTP.
- `CLICKHOUSE_EVENTS_TABLE` — таблица для сырых событий (по умолчанию `events`).
- `CLICKHOUSE_TIMEOUT_SECONDS` — таймаут httpx-клиента для ClickHouse.

## Краткое API
- `POST /auth/register` — создать пользователя, вернуть access/refresh.
- `POST /auth/login` — логин по email/паролю.
- `POST /auth/refresh` — обновить пару токенов.
- `POST /api/v1/events` — принять батч событий, ответ `{accepted: N}` (202).
- `POST /api/v1/metrics/calculate` — пересчитать указанные метрики по курсу за период.
- `GET /api/v1/metrics/user/{user_id}` — метрики пользователя за период. Требует Bearer access токен с ролью `teacher` или `admin`.
- `GET /api/v1/analytics/course/{course_id}` — агрегаты метрик по курсу за период (тот же доступ).

Параметры дат передаются в ISO 8601, список метрик — через query `metrics=retention&metrics=completion` или в теле (для расчёта).

## Тесты
```bash
pytest
```
