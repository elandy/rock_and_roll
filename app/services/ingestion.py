from dataclasses import dataclass, field
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.podcasts import (
    create_podcast,
    get_by_source_id,
    update_image_data,
)
from app.schemas.itunes import ITunesPodcast
from app.services.images import ImageService
from app.services.normalizer import (
    PodcastNormalizationError,
    enrich_podcast,
    normalize_podcast,
)
from app.services.rss import RSSClient, RSSClientError


@dataclass(frozen=True)
class SkippedPodcast:
    source_id: str | None
    reason: str


@dataclass
class IngestionResult:
    fetched: int = 0
    stored: int = 0
    skipped: int = 0
    skipped_items: list[SkippedPodcast] = field(
        default_factory=list
    )


class IngestionService:
    def __init__(
        self,
        db: Session,
        rss_client: RSSClient,
        image_service: ImageService,
    ) -> None:
        self.db = db
        self.rss_client = rss_client
        self.image_service = image_service

    async def ingest(
        self,
        podcasts: list[ITunesPodcast],
    ) -> IngestionResult:
        result = IngestionResult(
            fetched=len(podcasts),
        )

        for podcast in podcasts:
            await self._ingest_one(
                podcast=podcast,
                result=result,
            )

        return result

    async def _ingest_one(
        self,
        podcast: ITunesPodcast,
        result: IngestionResult,
    ) -> None:
        source_id = str(podcast.collection_id)

        existing = get_by_source_id(
            self.db,
            source="itunes",
            source_id=source_id,
        )

        if existing is not None:
            self._skip(
                result,
                source_id=source_id,
                reason="already_exists",
            )
            return

        try:
            normalized = normalize_podcast(podcast)
        except PodcastNormalizationError as exc:
            self._skip(
                result,
                source_id=source_id,
                reason=str(exc),
            )
            return

        normalized = await self._enrich_from_rss(
            normalized,
        )

        podcast_id = uuid4()

        try:
            stored_podcast = create_podcast(
                self.db,
                normalized,
                podcast_id=podcast_id,
            )

            image_result = await self.image_service.process(
                normalized.image_url,
                podcast_id,
            )

            if image_result.success:
                update_image_data(
                    stored_podcast,
                    image_path=image_result.image_path,
                    color_palette=image_result.color_palette,
                )

            self.db.commit()

        except IntegrityError:
            self.db.rollback()

            self._skip(
                result,
                source_id=source_id,
                reason="already_exists",
            )
            return

        except Exception:
            self.db.rollback()
            raise

        result.stored += 1

    async def _enrich_from_rss(
        self,
        podcast,
    ):
        if not podcast.feed_url:
            return podcast

        try:
            metadata = await self.rss_client.fetch_metadata(
                podcast.feed_url,
            )
        except RSSClientError:
            return podcast

        return enrich_podcast(
            podcast,
            description=metadata.description,
            language=metadata.language,
        )

    @staticmethod
    def _skip(
        result: IngestionResult,
        *,
        source_id: str | None,
        reason: str,
    ) -> None:
        result.skipped += 1

        result.skipped_items.append(
            SkippedPodcast(
                source_id=source_id,
                reason=reason,
            )
        )