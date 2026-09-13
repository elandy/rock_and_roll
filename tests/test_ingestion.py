import httpx
import pytest
import respx

from app.services.rss import RSSMetadata
from app.db.models import Podcast
from app.schemas.itunes import ITunesPodcast
from app.services.images import ImageProcessingResult
from app.services.ingestion import IngestionService
from app.services.rss import RSSClient
from app.utils.html import clean_html


class FakeRSSClient:
    async def fetch_metadata(
        self,
        feed_url: str,
    ) -> RSSMetadata:
        return RSSMetadata(
            description="A rock podcast.",
            language="en-us",
        )


class SuccessfulImageService:
    async def process(
        self,
        image_url: str | None,
        podcast_id,
    ) -> ImageProcessingResult:
        return ImageProcessingResult(
            success=True,
            image_path=(
                f"images/{podcast_id}.jpg"
            ),
            color_palette=[
                "#C83232",
                "#111111",
            ],
        )

class FailedImageService:
    async def process(self, image_url, podcast_id):
        return ImageProcessingResult(
            success=False,
            image_path=None,
            color_palette=[],
            error="image processing disabled in test",
        )

def make_podcast(
    collection_id: int = 12345,
    **overrides,
) -> ITunesPodcast:
    data = {
        "collectionId": collection_id,
        "artistName": "Rock Feed",
        "collectionName": "Rock Feed",
        "feedUrl": "https://example.com/feed.xml",
        "collectionViewUrl": "https://example.com/podcast",
        "artworkUrl600": "https://example.com/image.jpg",
        "primaryGenreName": "Rock",
        "genres": ["Rock", "Music"],
        "country": "USA",
    }

    data.update(overrides)

    return ITunesPodcast.model_validate(data)


@pytest.mark.asyncio
async def test_ingest_stores_podcast_with_enrichment(db):
    service = IngestionService(
        db=db,
        rss_client=FakeRSSClient(),
        image_service=SuccessfulImageService(),
    )

    result = await service.ingest(
        [make_podcast()]
    )

    assert result.fetched == 1
    assert result.stored == 1
    assert result.skipped == 0

    podcast = db.query(Podcast).one()

    assert podcast.source == "itunes"
    assert podcast.source_id == "12345"
    assert podcast.title == "Rock Feed"

    assert podcast.description == "A rock podcast."
    assert podcast.language == "en-us"

    assert podcast.image_path.startswith(
        "images/"
    )

    assert podcast.color_palette == [
        "#C83232",
        "#111111",
    ]


@pytest.mark.asyncio
async def test_ingest_is_idempotent(db):
    service = IngestionService(
        db=db,
        rss_client=FakeRSSClient(),
        image_service=SuccessfulImageService(),
    )

    podcast = make_podcast()

    first = await service.ingest([podcast])
    second = await service.ingest([podcast])

    assert first.stored == 1
    assert first.skipped == 0

    assert second.stored == 0
    assert second.skipped == 1

    assert second.skipped_items[0].reason == (
        "already_exists"
    )

    assert db.query(Podcast).count() == 1


@pytest.mark.asyncio
async def test_ingest_skips_invalid_podcast(db):
    service = IngestionService(
        db=db,
        rss_client=FakeRSSClient(),
        image_service=SuccessfulImageService(),
    )

    podcast = make_podcast(
        collectionName="   ",
    )

    result = await service.ingest([podcast])

    assert result.fetched == 1
    assert result.stored == 0
    assert result.skipped == 1

    assert result.skipped_items[0].reason == (
        "Podcast has no title"
    )

    assert db.query(Podcast).count() == 0


class FailingRSSClient:
    async def fetch_metadata(
        self,
        feed_url: str,
    ) -> RSSMetadata:
        from app.services.rss import RSSClientError

        raise RSSClientError("feed unavailable")


@pytest.mark.asyncio
async def test_rss_failure_does_not_fail_ingestion(db):
    service = IngestionService(
        db=db,
        rss_client=FailingRSSClient(),
        image_service=SuccessfulImageService(),
    )

    result = await service.ingest(
        [make_podcast()]
    )

    assert result.stored == 1
    assert result.skipped == 0

    podcast = db.query(Podcast).one()

    assert podcast.description is None
    assert podcast.language is None


class FailingImageService:
    async def process(
        self,
        image_url: str | None,
        podcast_id,
    ) -> ImageProcessingResult:
        return ImageProcessingResult(
            success=False,
            image_path=None,
            color_palette=[],
            error="image unavailable",
        )


@pytest.mark.asyncio
async def test_image_failure_does_not_fail_ingestion(db):
    service = IngestionService(
        db=db,
        rss_client=FakeRSSClient(),
        image_service=FailingImageService(),
    )

    result = await service.ingest(
        [make_podcast()]
    )

    assert result.stored == 1
    assert result.skipped == 0

    podcast = db.query(Podcast).one()

    assert podcast.image_path is None
    assert podcast.color_palette == []

    assert podcast.description == (
        "A rock podcast."
    )


@pytest.mark.asyncio
async def test_bulk_ingestion_reports_mixed_outcomes(db):
    service = IngestionService(
        db=db,
        rss_client=FakeRSSClient(),
        image_service=SuccessfulImageService(),
    )

    existing = make_podcast(
        collection_id=100,
    )

    await service.ingest([existing])

    new_podcast = make_podcast(
        collection_id=200,
        collectionName="Another Rock Show",
    )

    invalid = make_podcast(
        collection_id=300,
        collectionName=" ",
    )

    result = await service.ingest(
        [
            existing,
            new_podcast,
            invalid,
        ]
    )

    assert result.fetched == 3
    assert result.stored == 1
    assert result.skipped == 2

    reasons = {
        item.reason
        for item in result.skipped_items
    }

    assert reasons == {
        "already_exists",
        "Podcast has no title",
    }

    assert db.query(Podcast).count() == 2


@pytest.mark.asyncio
@respx.mock
async def test_ingestion_cleans_html_from_rss_description(db):
    feed_url = "https://example.com/rock-feed.xml"

    rss_body = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Rock Podcast</title>
    <description><![CDATA[
      <p>Rock &amp; roll <strong>every week</strong>.</p>
      <p>New episodes every Friday.</p>
      <script>alert("should not be stored")</script>
    ]]></description>
    <language>en-us</language>
  </channel>
</rss>
"""

    respx.get(feed_url).mock(
        return_value=httpx.Response(
            200,
            text=rss_body,
            headers={"Content-Type": "application/rss+xml"},
        )
    )

    podcast = ITunesPodcast(
        collectionId=123456,
        artistName="Rock Author",
        collectionName="Rock Podcast",
        feedUrl=feed_url,
        collectionViewUrl="https://example.com/podcast",
        artworkUrl600=None,
        primaryGenreName="Rock",
        genres=["Rock", "Music"],
        country="USA",
    )

    service = IngestionService(
        db=db,
        rss_client=RSSClient(),
        image_service=FailedImageService(),
    )

    result = await service.ingest([podcast])

    assert result.fetched == 1
    assert result.stored == 1
    assert result.skipped == 0

    stored = db.query(Podcast).filter(
        Podcast.source == "itunes",
        Podcast.source_id == "123456",
    ).one()

    assert stored.description == (
        "Rock & roll every week. New episodes every Friday."
    )
    assert stored.language == "en-us"
    assert "<strong>" not in stored.description
    assert "<script>" not in stored.description
    assert "alert" not in stored.description


def test_clean_html_removes_tags_scripts_and_decodes_entities():
    value = """
        <p>Rock &amp; roll <strong>every week</strong>.</p>
        <script>alert("bad")</script>
    """

    assert clean_html(value) == 'Rock & roll every week.'