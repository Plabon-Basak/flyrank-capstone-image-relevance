
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class APIUsage(Base):
    __tablename__ = "api_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(150), nullable=False)
    operation: Mapped[str] = mapped_column(String(30), nullable=False)

    image_id: Mapped[int | None] = mapped_column(
        ForeignKey("images.id", ondelete="SET NULL"),
        nullable=True,
    )

    blog_post_id: Mapped[int | None] = mapped_column(
        ForeignKey("blog_posts.id", ondelete="SET NULL"),
        nullable=True,
    )

    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    billable_characters: Mapped[int | None] = mapped_column(Integer, nullable=True)

    usage_source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="unavailable",
    )

    estimated_cost_usd: Mapped[float] = mapped_column(
        Numeric(12, 8),
        nullable=False,
        default=0,
    )

    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
