from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MatchSuggestionReview(BaseModel):
    status: Literal["approved", "rejected"]
    decision_reason: str | None = Field(
        default=None,
        max_length=2000,
    )


class MatchSuggestionRead(BaseModel):
    id: int
    image_id: int
    blog_post_id: int
    similarity: float = Field(ge=0, le=1)
    matching_reason: str
    status: str
    decision_reason: str | None
    created_at: datetime
    reviewed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
