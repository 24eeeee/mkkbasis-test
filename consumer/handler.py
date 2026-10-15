import asyncio
import random
import logging

from faststream.rabbit import RabbitBroker, RabbitMessage

from consumer.broker import retry_queues, RETRY_DELAYS, dlq
from consumer.core.services.payments import PaymentService
from consumer.core.services.webhook import WebhookService
from consumer.db.session import SessionLocal
from consumer.enums.payment_status import PaymentStatus

MAX_ATTEMPTS = len(RETRY_DELAYS) + 1

logger = logging.getLogger(__name__)


async def simulate_gateway() -> None:
    await asyncio.sleep(random.uniform(2, 5))
    if random.random() < 0.1:
        raise RuntimeError("Gateway declined")


async def _retry_or_dlq(broker: RabbitBroker, msg: RabbitMessage, body: dict, next_attempt: int, phase: str) -> None:
    if next_attempt >= MAX_ATTEMPTS:
        await broker.publish(
            body,
            queue=dlq,
            headers={**msg.headers, 'x-last-error': f'{phase} failed'},
            persist=True,
        )
        await msg.ack()
        return

    target_queue = retry_queues[next_attempt - 1]
    await broker.publish(
        body,
        queue=target_queue,
        headers={**msg.headers, 'x-attempt': next_attempt},
        persist=True,
    )
    await msg.ack()


async def handle(body: dict, msg: RabbitMessage, broker: RabbitBroker) -> None:
    payment_id = body['payment_id']
    event_id = body['event_id']
    attempt = int(msg.headers.get('x-attempt', 0))

    webhook_service = WebhookService()

    async with SessionLocal() as session:
        payment_service = PaymentService(session)
        payment = await payment_service.get(payment_id)
        if not payment:
            logger.error(f'Payment {payment_id} not found')
            await msg.ack()
            return

        if payment.status == PaymentStatus.PENDING:
            try:
                await simulate_gateway()
                await payment_service.mark_succeeded(payment_id)
            except Exception as e:
                logger.warning(f'Gateway failed for payment_id {payment_id} on attempt {attempt}: {e}')

                if attempt+1 >= MAX_ATTEMPTS:
                    await payment_service.mark_failed(payment_id)
                    payment = await payment_service.get(payment_id)

                    try:
                        await webhook_service.send_webhook(payment, event_id)
                    except Exception as wh_e:
                        logger.warning(f'Webhook after last attempt failed: {wh_e}')

                await _retry_or_dlq(broker, msg, body, attempt+1, 'gateway')
                return
        payment = await payment_service.get(payment_id)

    try:
        await webhook_service.send_webhook(payment, event_id)
        await msg.ack()
    except Exception as e:
        logger.warning(f'Webhook failed: {e}')
        await _retry_or_dlq(broker, msg, body, attempt+1, 'webhook')
