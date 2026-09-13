from dataclasses import dataclass

from app.schemas.itunes import ITunesPodcast


class PodcastNormalizationError(Exception):
    """Raised when an iTunes podcast cannot be normalized."""


@dataclass(frozen=True)
class NormalizedPodcast:
    source: str
    source_id: str
    title: str
    author: str | None
    description: str | None
    feed_url: str | None
    podcast_url: str | None
    image_url: str | None
    category: str | None
    genres: list[str]
    country: str | None
    language: str | None


def normalize_podcast(
    podcast: ITunesPodcast,
) -> NormalizedPodcast:
    title = _clean_text(podcast.collection_name)

    if not title:
        raise PodcastNormalizationError(
            "Podcast has no title"
        )

    author = _clean_text(podcast.artist_name)

    feed_url = _clean_url(podcast.feed_url)
    podcast_url = _clean_url(podcast.collection_view_url)
    image_url = _clean_url(
        podcast.artwork_url600
        or podcast.artwork_url100
    )

    genres = _normalize_genres(podcast.genres)

    category = _clean_text(
        podcast.primary_genre_name
    )

    country = _clean_text(podcast.country)

    return NormalizedPodcast(
        source="itunes",
        source_id=str(podcast.collection_id),
        title=title,
        author=author,
        description=None,
        feed_url=feed_url,
        podcast_url=podcast_url,
        image_url=image_url,
        category=category,
        genres=genres,
        country=country,
        language=None,
    )


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None

    value = " ".join(value.split())

    return value or None


def _clean_url(value: str | None) -> str | None:
    value = _clean_text(value)

    if not value:
        return None

    if not value.startswith(("http://", "https://")):
        return None

    return value


def _normalize_genres(
    genres: list[str],
) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()

    for genre in genres:
        cleaned = _clean_text(genre)

        if not cleaned:
            continue

        key = cleaned.casefold()

        if key in seen:
            continue

        seen.add(key)
        normalized.append(cleaned)

    return normalized

def enrich_podcast(
    podcast: NormalizedPodcast,
    *,
    description: str | None = None,
    language: str | None = None,
) -> NormalizedPodcast:
    return NormalizedPodcast(
        source=podcast.source,
        source_id=podcast.source_id,
        title=podcast.title,
        author=podcast.author,
        description=description or podcast.description,
        feed_url=podcast.feed_url,
        podcast_url=podcast.podcast_url,
        image_url=podcast.image_url,
        category=podcast.category,
        genres=podcast.genres,
        country=podcast.country,
        language=language or podcast.language,
    )