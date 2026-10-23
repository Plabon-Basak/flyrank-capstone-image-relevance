
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MatchSuggestion(Base):
    __tablename__ = "match_suggestions"

    __table_args__ = (
        UniqueConstraint(
            "image_id",
            "blog_post_id",
            name="uq_match_suggestion_image_post",
        ),
        CheckConstraint(
            "similarity >= 0 AND similarity <= 1",
            name="ck_match_suggestion_similarity",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_match_suggestion_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    image_id: Mapped[int] = mapped_column(
        ForeignKey("images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    blog_post_id: Mapped[int] = mapped_column(
        ForeignKey("blog_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    similarity: Mapped[float] = mapped_column(Float, nullable=False)
    matching_reason: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )

    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
