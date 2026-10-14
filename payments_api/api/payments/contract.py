from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel, ConfigDict, Field, computed_field,
    field_serializer, field_validator, model_validator,
)
from typing import Self

from ...enums.currency import Currency
from ...enums.payment_status import PaymentStatus


class PaymentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: Currency
    description: str = Field(..., min_length=1, max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)
    webhook_url: str = Field(..., min_length=1)

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("must start with http:// or https://")
        return v

    @model_validator(mode="after")
    def validate_metadata_size(self) -> Self:
        if len(str(self.metadata)) > 4096:
            raise ValueError("metadata too large (max 4096 bytes)")
        return self


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any] = Field(..., validation_alias="metadata_")
    status: PaymentStatus
    idempotency_key: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None = None

    @field_serializer("amount")
    def serialize_amount(self, value: Decimal) -> str:
        return f"{value:.2f}"

    @computed_field
    @property
    def is_final(self) -> bool:
        return self.status in (PaymentStatus.SUCCEEDED, PaymentStatus.FAILED)
