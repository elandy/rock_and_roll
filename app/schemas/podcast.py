from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PodcastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    author: str | None
    description: str | None

    feed_url: str | None
    podcast_url: str | None

    image_url: str | None
    image_path: str | None

    category: str | None
    genres: list[str]

    country: str | None
    language: str | None

    color_palette: list[str]

    created_at: datetime
    updated_at: datetime


class PodcastListResponse(BaseModel):
    items: list[PodcastResponse]
    page: int
    page_size: int
    total: int