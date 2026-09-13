import pytest

from app.schemas.itunes import ITunesPodcast
from app.services.normalizer import (
    PodcastNormalizationError,
    normalize_podcast, enrich_podcast,
)


def make_podcast(
    **overrides,
) -> ITunesPodcast:
    data = {
        "collectionId": 12345,
        "artistName": " Rock Feed ",
        "collectionName": "  Rock Feed  ",
        "feedUrl": "https://example.com/feed.xml",
        "collectionViewUrl": "https://example.com/podcast",
        "artworkUrl600": "https://example.com/image.jpg",
        "primaryGenreName": "Rock",
        "genres": [
            "Rock",
            "Music",
            "rock",
        ],
        "country": " USA ",
    }

    data.update(overrides)

    return ITunesPodcast.model_validate(data)


def test_normalize_podcast():
    podcast = make_podcast()

    result = normalize_podcast(podcast)

    assert result.source == "itunes"
    assert result.source_id == "12345"
    assert result.title == "Rock Feed"
    assert result.author == "Rock Feed"

    assert result.feed_url == "https://example.com/feed.xml"
    assert result.podcast_url == "https://example.com/podcast"
    assert result.image_url == "https://example.com/image.jpg"

    assert result.category == "Rock"
    assert result.genres == ["Rock", "Music"]
    assert result.country == "USA"


def test_normalize_podcast_uses_fallback_image():
    podcast = make_podcast(
        artworkUrl600=None,
        artworkUrl100="https://example.com/small.jpg",
    )

    result = normalize_podcast(podcast)

    assert result.image_url == "https://example.com/small.jpg"


def test_normalize_podcast_handles_missing_optional_fields():
    podcast = make_podcast(
        artistName=None,
        feedUrl=None,
        collectionViewUrl=None,
        artworkUrl600=None,
        artworkUrl100=None,
        primaryGenreName=None,
        genres=[],
        country=None,
    )

    result = normalize_podcast(podcast)

    assert result.title == "Rock Feed"
    assert result.author is None
    assert result.feed_url is None
    assert result.podcast_url is None
    assert result.image_url is None
    assert result.category is None
    assert result.genres == []
    assert result.country is None


def test_normalize_podcast_rejects_missing_title():
    podcast = make_podcast(
        collectionName="   ",
    )

    with pytest.raises(
        PodcastNormalizationError,
        match="Podcast has no title",
    ):
        normalize_podcast(podcast)


def test_normalize_podcast_rejects_invalid_urls():
    podcast = make_podcast(
        feedUrl="not-a-url",
        collectionViewUrl="ftp://example.com",
        artworkUrl600="invalid",
    )

    result = normalize_podcast(podcast)

    assert result.feed_url is None
    assert result.podcast_url is None
    assert result.image_url is None

def test_enrich_podcast():
    podcast = make_podcast()

    normalized = normalize_podcast(podcast)

    enriched = enrich_podcast(
        normalized,
        description="A rock podcast.",
        language="en-us",
    )

    assert enriched.description == "A rock podcast."
    assert enriched.language == "en-us"