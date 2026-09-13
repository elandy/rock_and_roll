from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth import require_api_key
from app.db.session import get_db
from app.schemas.ingestion import (
    IngestionResponse,
    SkippedPodcastResponse,
)
from app.services.images import ImageService
from app.services.ingestion import IngestionService
from app.services.itunes import ITunesClient
from app.services.rss import RSSClient


router = APIRouter(
    prefix="/ingestion",
    tags=["Ingestion"],
    dependencies=[Depends(require_api_key)],
)


def get_ingestion_service(
    db: Session = Depends(get_db),
) -> IngestionService:
    image_service = ImageService(
        storage_dir=Path("/app/storage/images"),
    )

    return IngestionService(
        db=db,
        rss_client=RSSClient(),
        image_service=image_service,
    )

def get_itunes_client() -> ITunesClient:
    return ITunesClient()


def build_response(
    result,
) -> IngestionResponse:
    return IngestionResponse(
        fetched=result.fetched,
        stored=result.stored,
        skipped=result.skipped,
        skipped_items=[
            SkippedPodcastResponse(
                source_id=item.source_id,
                reason=item.reason,
            )
            for item in result.skipped_items
        ],
    )


@router.post(
    "/bulk",
    response_model=IngestionResponse,
)
async def bulk_ingest(
    term: str = Query(
        default="rock",
        min_length=1,
        max_length=100,
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
    ),
    client: ITunesClient = Depends(get_itunes_client),
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestionResponse:
    response = await client.search_podcasts(
        term=term,
        limit=limit,
    )
    result = await service.ingest(
        response.results,
    )

    return build_response(result)


@router.post(
    "/single",
    response_model=IngestionResponse,
)
async def single_ingest(
    collection_id: int = Query(..., gt=0),
    client: ITunesClient = Depends(get_itunes_client),
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestionResponse:
    podcast = await client.lookup_podcast(
        collection_id,
    )
    if podcast is None:
        return IngestionResponse(
            fetched=0,
            stored=0,
            skipped=1,
            skipped_items=[
                SkippedPodcastResponse(
                    source_id=str(collection_id),
                    reason="Podcast not found",
                )
            ],
        )
    result = await service.ingest([podcast])

    return build_response(result)