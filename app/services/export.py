import json
from collections.abc import Iterator

from app.repositories.podcasts import iter_podcasts_for_export
from sqlalchemy.orm import Session


def iter_podcast_ndjson(
    db: Session,
    *,
    batch_size: int = 500,
) -> Iterator[bytes]:
    for podcast in iter_podcasts_for_export(
        db,
        batch_size=batch_size,
    ):
        payload = {
            "id": str(podcast.id),
            "title": podcast.title,
            "author": podcast.author,
            "description": podcast.description,
            "feed_url": podcast.feed_url,
            "podcast_url": podcast.podcast_url,
            "image_url": podcast.image_url,
            "image_path": podcast.image_path,
            "category": podcast.category,
            "genres": podcast.genres,
            "country": podcast.country,
            "language": podcast.language,
            "color_palette": podcast.color_palette,
            "created_at": podcast.created_at.isoformat(),
            "updated_at": podcast.updated_at.isoformat(),
        }

        yield (
            json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )