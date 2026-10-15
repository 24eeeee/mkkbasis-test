import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Numeric, Enum as SAEnum, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base
from ...enums.currency import Currency
from ...enums.payment_status import PaymentStatus


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency", native_enum=False), nullable=False
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status", native_enum=False),
        default=PaymentStatus.PENDING,
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    webhook_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
