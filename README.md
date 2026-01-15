# student-metrics-backend

## Запуск в Docker

1. Скопируйте `.env.example` в `.env` и при необходимости обновите значения.
2. Соберите и запустите стек:
   ```bash
   docker-compose up --build
   ```
3. API будет доступно на `http://localhost:8000`. По умолчанию:
   - PostgreSQL: `postgres://app:app@localhost:5432/app`
   - ClickHouse HTTP: `http://localhost:8123`

Быстрые команды:
- Остановить и удалить контейнеры/сети (с сохранением данных в volumes):
  ```bash
  docker-compose down
  ```
- Полная очистка с удалением volumes:
  ```bash
  docker-compose down -v
  ```
