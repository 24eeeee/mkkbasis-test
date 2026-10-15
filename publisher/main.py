import asyncio
import logging

from publisher.broker import make_broker, exchange
from publisher.core.config import settings
from publisher.loop import run_publisher

logger = logging.getLogger(__name__)


async def main() -> None:
    broker = make_broker(settings.rabbitmq_url)
    async with broker:
        await broker.declare_exchange(exchange)
        logger.info('Starting publisher...')
        await run_publisher(broker)


if __name__ == "__main__":
    asyncio.run(main())
