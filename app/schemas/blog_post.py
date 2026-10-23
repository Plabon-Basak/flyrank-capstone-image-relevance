from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BlogPostCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    url: str | None = Field(default=None, max_length=1000)


class BlogPostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    url: str | None
    created_at: datetime
