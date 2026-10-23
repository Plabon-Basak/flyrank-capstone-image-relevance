
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BatchJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_ids: list[int] = Field(min_length=1, max_length=100)
    max_retries: int = Field(default=3, ge=0, le=5)

    @model_validator(mode="after")
    def validate_unique_image_ids(self):
        if len(self.image_ids) != len(set(self.image_ids)):
            raise ValueError("Image IDs must be unique.")

        if any(image_id <= 0 for image_id in self.image_ids):
            raise ValueError("Image IDs must be positive integers.")

        return self


class BatchJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    image_ids: list[int]
    total_items: int
    processed_items: int
    failed_items: int
    retry_count: int
    max_retries: int
    estimated_cost_usd: float
    error_details: dict | None
    last_error: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
