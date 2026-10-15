# Payments Service

Асинхронный микросервис процессинга платежей. Принимает запросы на оплату, обрабатывает через эмуляцию внешнего платёжного шлюза, уведомляет клиента через webhook.

## Стек

- Python 3.12, FastAPI, Pydantic v2
- SQLAlchemy 2.0 (async), PostgreSQL 16
- RabbitMQ 3.13, FastStream
- Alembic, Poetry
- Docker, docker-compose

## Архитектура

```
                ┌──────────┐         ┌────────────┐
   client ────► │   api    │ ──────► │ PostgreSQL │
                └──────────┘         │            │
                                     │  payments  │
                                     │  outbox    │
                                     └─────┬──────┘
                                           │ polling
                                           ▼
                                    ┌────────────┐        ┌──────────┐
                                    │ publisher  │ ─────► │ RabbitMQ │
                                    └────────────┘        └────┬─────┘
                                                               │
                                                               ▼
                                                         ┌──────────┐
                                                         │ consumer │
                                                         └────┬─────┘
                                                              │ webhook
                                                              ▼
                                                          [client]
```

Три сервиса:
- **api** — принимает HTTP-запросы, пишет платёж + outbox-запись в одной транзакции.
- **publisher** — читает outbox, публикует события в RabbitMQ.
- **consumer** — обрабатывает события: эмулирует шлюз, обновляет статус, шлёт webhook.

## Быстрый старт

```bash
cp .env.example .env
docker compose up
```

API будет доступен на `http://localhost:8000`, RabbitMQ Management UI — на `http://localhost:15672` (guest / guest).

Интерактивная документация: `http://localhost:8000/docs`.

## Переменные окружения

| Переменная | Описание | Default |
|---|---|---|
| `POSTGRES_USER` | Пользователь БД | `app` |
| `POSTGRES_PASSWORD` | Пароль БД | `app` |
| `POSTGRES_DB` | Имя БД | `payments` |
| `POSTGRES_HOST` | Хост БД | `postgres` |
| `POSTGRES_PORT` | Порт БД (наружу) | `5432` |
| `DATABASE_URL` | Полный DSN для SQLAlchemy | — |
| `RABBITMQ_USER` | Пользователь брокера | `guest` |
| `RABBITMQ_PASSWORD` | Пароль брокера | `guest` |
| `RABBITMQ_HOST` | Хост брокера | `rabbitmq` |
| `RABBITMQ_PORT` | Порт брокера (наружу) | `5672` |
| `RABBITMQ_URL` | Полный AMQP URL | — |
| `API_KEY` | Статический API-ключ | `secret-key` |

## API

Все эндпоинты требуют заголовок `X-API-Key`.

### Создание платежа

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "X-API-Key: secret-key" \
  -H "Idempotency-Key: order-42-payment-1" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "100",
    "currency": "RUB",
    "description": "Оплата заказа #42",
    "metadata": {"order_id": "42"},
    "webhook_url": "https://webhook.site/your-unique-url"
  }'
```

Ответ `202 Accepted`:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "amount": "100.00",
  "currency": "RUB",
  "description": "Оплата заказа #42",
  "metadata": {
    "order_id": "42"
  },
  "status": "pending",
  "idempotency_key": "order-42-payment-1",
  "webhook_url": "https://webhook.site/your-unique-url",
  "created_at": "2026-10-15T19:31:54.651883Z",
  "processed_at": null,
  "is_final": false
}
```

Повторный запрос с тем же `Idempotency-Key` вернёт **тот же платёж**, а не создаст новый.

### Получение платежа

```bash
curl http://localhost:8000/api/v1/payments/<payment_id> \
  -H "X-API-Key: secret-key"
```

### Ошибки

- `401 Unauthorized` — неверный или отсутствующий `X-API-Key`.
- `422 Unprocessable Entity` — невалидное тело.
- `404 Not Found` — платёж не найден.

## Как это работает

### Outbox pattern

При создании платежа api пишет **две** записи в БД в одной транзакции:
- `payments` — сам платёж,
- `outbox` — событие `payment.created`.

Это решает dual write problem: невозможно атомарно записать в БД и опубликовать в брокер. Вместо этого событие «лежит» в БД, а отдельный процесс — publisher — вычитывает его и публикует в RabbitMQ.

Publisher использует `FOR UPDATE SKIP LOCKED` для безопасной параллельной работы, и помечает запись `PUBLISHED` только после успешной публикации. Если публикация упала — увеличивается `retry_count`, пишется `last_error`, запись остаётся `PENDING` и попробуется снова.

### Retry и Dead Letter Queue

Обработка платежа ретраится через RabbitMQ (at-least-once):

- `payments.new` — основная очередь, слушает consumer.
- `payments.retry.2s`, `.4s`, `.8s` — retry-очереди с TTL и DLX, возвращающим сообщение в `payments.new`.
- `payments.dlq` — окончательно упавшие сообщения.

На каждой ошибке (шлюз или webhook) consumer публикует сообщение в следующую retry-очередь с увеличенным `x-attempt`. Задержка растёт экспоненциально: 2s → 4s → 8s. После 4-й неудачи (1 начальная + 3 retry) сообщение уходит в DLQ.

Очереди durable, сообщения persistent (+volume на контейнер RabbitMQ) — переживают рестарт брокера.

### Идемпотентность

- **Уровень API:** `unique(idempotency_key)` на `payments` + обработка `IntegrityError`.
- **Уровень consumer:** `UPDATE payments SET status=... WHERE id=... AND status='PENDING'` — условный переход по state machine. Повторная попытка доставки сообщения не станет заново стучаться в платежный шлюз.
- **Уровень webhook:** в теле передаётся стабильный `event_id` (id outbox-записи), клиент может дедуплицировать повторные уведомления.

## Проверка DLQ

Временно установи `simulate_gateway` в 100% фейл:

```python
if random.random() < 1.0:
    raise RuntimeError("Gateway declined")
```

Создай платёж, через ~30 секунд в очереди `payments.dlq` будет сообщение с этим платежом:

```bash
docker compose exec rabbitmq rabbitmqctl list_queues name messages
```

`payments.dlq` должен содержать 1 сообщение. Посмотреть содержимое в UI: Queues → `payments.dlq` → Get messages → **Ack Mode: Nack message requeue true** (иначе сообщение удалится).
