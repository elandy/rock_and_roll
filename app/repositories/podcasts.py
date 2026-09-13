import uuid

from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.db.models import Podcast
from app.services.normalizer import NormalizedPodcast

from collections.abc import Iterator

from sqlalchemy import select


def get_by_source_id(
    db: Session,
    source: str,
    source_id: str,
) -> Podcast | None:
    statement = select(Podcast).where(
        Podcast.source == source,
        Podcast.source_id == source_id,
    )

    return db.scalar(statement)


def create_podcast(
    db: Session,
    data: NormalizedPodcast,
    podcast_id: uuid.UUID | None = None,
) -> Podcast:
    podcast = Podcast(
        id=podcast_id or uuid.uuid4(),
        source=data.source,
        source_id=data.source_id,
        title=data.title,
        author=data.author,
        description=data.description,
        feed_url=data.feed_url,
        podcast_url=data.podcast_url,
        image_url=data.image_url,
        category=data.category,
        genres=data.genres,
        country=data.country,
        language=data.language,
    )

    db.add(podcast)
    db.flush()

    return podcast

def update_image_data(
    podcast: Podcast,
    *,
    image_path: str | None,
    color_palette: list[str],
) -> None:
    podcast.image_path = image_path
    podcast.color_palette = color_palette

def list_podcasts(
    db: Session,
    *,
    page: int,
    page_size: int,
    search: str | None = None,
    category: str | None = None,
    country: str | None = None,
) -> tuple[list[Podcast], int]:
    filters = []

    if search:
        search_pattern = f"%{search}%"
        filters.append(
            or_(
                Podcast.title.ilike(search_pattern),
                Podcast.author.ilike(search_pattern),
                Podcast.description.ilike(search_pattern),
            )
        )

    if category:
        filters.append(Podcast.category.ilike(category))

    if country:
        filters.append(Podcast.country.ilike(country))

    count_statement = select(func.count()).select_from(Podcast)

    if filters:
        count_statement = count_statement.where(*filters)

    total = db.scalar(count_statement) or 0

    offset = (page - 1) * page_size

    statement = (
        select(Podcast)
        .where(*filters)
        .order_by(Podcast.title.asc(), Podcast.id.asc())
        .offset(offset)
        .limit(page_size)
    )

    items = list(db.scalars(statement).all())

    return items, total

def get_by_id(db: Session, podcast_id: uuid.UUID) -> Podcast | None:
    statement = select(Podcast).where(Podcast.id == podcast_id)
    return db.scalar(statement)


def iter_podcasts_for_export(
    db: Session,
    *,
    batch_size: int = 500,
) -> Iterator[Podcast]:
    statement = (
        select(Podcast)
        .order_by(Podcast.id.asc())
        .execution_options(yield_per=batch_size)
    )

    yield from db.scalars(statement)