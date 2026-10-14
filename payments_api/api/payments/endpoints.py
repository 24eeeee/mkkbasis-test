from fastapi import APIRouter, Depends, status, Header, HTTPException

from .contract import PaymentCreate, PaymentResponse
from .deps import verify_api_key
from .deps import PaymentServiceDep
from ...core.services.payments import PaymentService

router = APIRouter(
    prefix='/api/v1/payments',
    tags=['payments'],
    dependencies=[Depends(verify_api_key)],
)


@router.post('', status_code=status.HTTP_202_ACCEPTED, response_model=PaymentResponse)
async def post_payment(
        payload: PaymentCreate,
        idempotency_key: str = Header(..., alias='Idempotency-Key'),
        service: PaymentService = PaymentServiceDep
):
    return await service.create(payload, idempotency_key)

@router.get('/{payment_id}', response_model=PaymentResponse)
async def get_payment(
        payment_id: str,
        service: PaymentService = PaymentServiceDep
):
    payment = await service.get(payment_id)
    if not payment:
        raise HTTPException(404, 'Payment not found')
    return payment
