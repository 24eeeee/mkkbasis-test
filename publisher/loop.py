import asyncio
import logging
from datetime import datetime, timezone

from faststream.rabbit import RabbitBroker
from sqlalchemy import select

from publisher.broker import exchange
from publisher.core.config import BATCH_SIZE, POLL_INTERVAL
from publisher.db.session import SessionLocal
from publisher.db.models.outbox import Outbox, OutboxStatus

logger = logging.getLogger(__name__)


async def run_publisher(broker: RabbitBroker) -> None:
    while True:
        try:
            await _publish_batch(broker)
        except Exception as e:
            logger.exception(f'publisher iteration failed: {e}')
        await asyncio.sleep(POLL_INTERVAL)

async def _publish_batch(broker: RabbitBroker) -> None:
    async with SessionLocal() as session:
        rows = (await session.scalars(
            select(Outbox)
            .where(Outbox.status == OutboxStatus.PENDING)
            .order_by(Outbox.created_at)
            .limit(BATCH_SIZE)
            .with_for_update(skip_locked=True)
        )).all()

        if not rows:
            return

        published_rows = 0

        for row in rows:
            try:
                await broker.publish(
                    {**row.payload, 'event_id': row.id},
                    exchange=exchange,
                    routing_key=row.event_type,
                    persist=True,
                )
                row.status = OutboxStatus.PUBLISHED
                row.published_at = datetime.now(timezone.utc)
                published_rows += 1
            except Exception as e:
                row.retry_count += 1
                row.last_error = str(e)[:500]
                logger.warning(f"publish failed outbox{row.id}: {e}")

        await session.commit()
        logger.info(f"published {published_rows} outbox records")
