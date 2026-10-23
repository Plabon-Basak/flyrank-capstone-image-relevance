
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BatchJob(Base):
    __tablename__ = "batch_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending", index=True
    )
    total_items: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    processed_items: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    failed_items: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    max_retries: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3
    )
    estimated_cost_usd: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    image_ids: Mapped[list[int]] = mapped_column(
        JSON, nullable=False, default=list
    )
    error_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
