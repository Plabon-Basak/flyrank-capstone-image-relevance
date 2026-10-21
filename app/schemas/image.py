from pydantic import BaseModel, ConfigDict, Field


class ImageMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=100)
    attributes: dict[str, str | int | float | bool] = Field(default_factory=dict)
    caption: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0, le=1)
