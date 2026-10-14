from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models.payment import Payment
from ...db.models.outbox import Outbox
from ...api.payments.contract import PaymentCreate, PaymentStatus


class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, payment_id: str) -> Payment | None:
        return await self.session.get(Payment, payment_id)

    async def get_by_idempotency_key(self, key: str) -> Payment | None:
        return await self.session.scalar(
            select(Payment).where(Payment.idempotency_key == key)
        )

    async def create(self, payload: PaymentCreate, idempotency_key: str) -> Payment:
        existing = await self.get_by_idempotency_key(idempotency_key)
        if existing:
            return existing

        payment = Payment(
            amount=payload.amount,
            currency=payload.currency,
            description=payload.description,
            metadata_=payload.metadata,
            idempotency_key=idempotency_key,
            webhook_url=payload.webhook_url,
            status=PaymentStatus.PENDING,
        )
        self.session.add(payment)
        await self.session.flush()

        self.session.add(Outbox(
            event_type="payment.created",
            payload={"payment_id": str(payment.id)},
        ))

        await self.session.commit()
        await self.session.refresh(payment)
        return payment
