import asyncio
import logging

from faststream import FastStream
from faststream.rabbit import RabbitMessage

from consumer.broker import make_broker, payments_exchange, main_queue, retry_queues, dlq
from consumer.core.config import settings
from consumer.handler import handle

logger = logging.getLogger(__name__)


async def main() -> None:
    broker = make_broker(settings.rabbitmq_url)
    app = FastStream(broker)

    @broker.subscriber(main_queue, payments_exchange)
    async def _handler(body: dict, msg: RabbitMessage):
        await handle(body, msg, broker)

    @app.after_startup
    async def declare_all():
        for q in retry_queues:
            await broker.declare_queue(q)

        await broker.declare_queue(dlq)

    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
