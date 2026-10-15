from sqlalchemy import update, func
from sqlalchemy.ext.asyncio import AsyncSession

from consumer.db.models.payment import Payment
from consumer.enums.payment_status import PaymentStatus


class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, payment_id: str) -> Payment | None:
        return await self.session.get(Payment, payment_id)

    async def mark_succeeded(self, payment_id: str) -> bool:
        result = await self.session.execute(
            update(Payment)
            .where(
                Payment.id == payment_id,
                Payment.status == PaymentStatus.PENDING
            )
            .values(
                status=PaymentStatus.SUCCEEDED,
                processed_at=func.now()
            )
        )
        await self.session.commit()
        return result.rowcount > 0

    async def mark_failed(self, payment_id: str) -> bool:
        result = await self.session.execute(
            update(Payment)
            .where(
                Payment.id == payment_id,
                Payment.status == PaymentStatus.PENDING
            )
            .values(
                status=PaymentStatus.FAILED,
                processed_at=func.now()
            )
        )
        await self.session.commit()
        return result.rowcount > 0
