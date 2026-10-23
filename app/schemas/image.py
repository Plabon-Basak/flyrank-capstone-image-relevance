from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ImageMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=100)
    attributes: dict[str, str | int | float | bool] = Field(default_factory=dict)
    caption: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0, le=1)


class ImageCreate(ImageMetadata):
    filename: str = Field(min_length=1, max_length=255)
    file_path: str = Field(min_length=1, max_length=500)


class ImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_path: str
    category: str | None
    subject: str | None
    attributes: dict | None
    caption: str | None
    confidence: float | None
    review_required: bool
    status: str
    created_at: datetime