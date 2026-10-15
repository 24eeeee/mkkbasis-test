import asyncio

from publisher.broker import make_broker, exchange
from publisher.core.config import settings
from publisher.loop import run_publisher


async def main() -> None:
    broker = make_broker(settings.rabbitmq_url)
    async with broker:
        await broker.declare_exchange(exchange)
        await run_publisher(broker)


if __name__ == "__main__":
    asyncio.run(main())
