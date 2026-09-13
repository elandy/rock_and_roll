from uuid import UUID

from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import require_api_key
from app.db.session import get_db
from app.repositories.podcasts import list_podcasts, get_by_id
from app.schemas.podcast import PodcastListResponse, PodcastResponse

router = APIRouter(
    prefix="/podcasts",
    tags=["Podcasts"],
    dependencies=[Depends(require_api_key)],
)


@router.get("", response_model=PodcastListResponse)
def get_podcasts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    category: str | None = Query(default=None, min_length=1, max_length=255),
    country: str | None = Query(default=None, min_length=1, max_length=100),
    db: Session = Depends(get_db),
) -> PodcastListResponse:
    podcasts, total = list_podcasts(
        db,
        page=page,
        page_size=page_size,
        search=search,
        category=category,
        country=country,
    )

    return PodcastListResponse(
        items=podcasts,
        page=page,
        page_size=page_size,
        total=total,
    )

@router.get("/{podcast_id}", response_model=PodcastResponse)
def get_podcast(
    podcast_id: UUID,
    db: Session = Depends(get_db),
) -> PodcastResponse:
    podcast = get_by_id(db, podcast_id)

    if podcast is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "podcast_not_found",
                "message": "Podcast not found",
            },
        )

    return podcast