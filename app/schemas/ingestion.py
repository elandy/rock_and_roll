from pydantic import BaseModel, ConfigDict


class SkippedPodcastResponse(BaseModel):
    source_id: str | None
    reason: str


class IngestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fetched: int
    stored: int
    skipped: int
    skipped_items: list[SkippedPodcastResponse]