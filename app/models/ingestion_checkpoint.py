from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IngestionCheckpoint(Base):
    """Persistent synchronization state for an external data source."""

    __tablename__ = "ingestion_checkpoints"

    source: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    last_successful_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_run_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_run_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_status: Mapped[str] = mapped_column(
        String(20),
        default="never",
        server_default="never",
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    total_records_fetched: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )

    total_records_upserted: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
