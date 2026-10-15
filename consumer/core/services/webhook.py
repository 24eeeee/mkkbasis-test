import asyncio
import logging

import httpx

from consumer.db.models.payment import Payment

WEBHOOK_MAX_ATTEMPTS = 3
WEBHOOK_BASE_DELAY = 1

logger = logging.getLogger(__name__)


class WebhookService:
    @staticmethod
    async def send_webhook(payment: Payment, event_id: str) -> None:
        payload = {
            'event_id': str(event_id),
            'payment_id': str(payment.id),
            'status': payment.status.value,
            'amount': str(payment.amount),
            'currency': payment.currency.value,
            'processed_at': payment.processed_at.isoformat() if payment.processed_at else None
        }

        last_error: str | None = None

        async with httpx.AsyncClient(timeout=10.) as client:
            for attempt in range(WEBHOOK_MAX_ATTEMPTS):
                try:
                    resp = await client.post(payment.webhook_url, json=payload)
                    if 200 <= resp.status_code < 300:
                        logger.info(f'Webhook delivered for payment {payment.id}, attempt: {attempt}')
                        return
                    last_error = f'HTTP response status code {resp.status_code}'
                except httpx.HTTPError as e:
                    last_error = str(e)

                if attempt < WEBHOOK_MAX_ATTEMPTS - 1:
                    await asyncio.sleep(WEBHOOK_BASE_DELAY * (2 ** attempt))

        raise RuntimeError(f'Webhook {payment.webhook_url} for payment {payment.id} failed, last error: {last_error}')
