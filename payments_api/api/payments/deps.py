from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...db.session import get_session
from ...core.services.payments import PaymentService


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != settings.api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")

async def get_payment_service(
    session: AsyncSession = Depends(get_session),
) -> PaymentService:
    return PaymentService(session)


PaymentServiceDep = Depends(get_payment_service)
