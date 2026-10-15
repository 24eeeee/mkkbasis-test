import uuid
from enum import Enum
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, func, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class OutboxStatus(str, Enum):
    PENDING = "pending"
    PUBLISHED = "published"


class Outbox(Base):
    __tablename__ = "outbox"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        SAEnum(OutboxStatus, name="outbox_status", native_enum=False),
        default=OutboxStatus.PENDING,
        nullable=False,
        index=True,
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )