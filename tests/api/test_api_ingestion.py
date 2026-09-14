from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from app.api.ingestion import (
    get_ingestion_service,
    get_itunes_client,
)
from app.main import app
from app.schemas.itunes import ITunesPodcast, ITunesSearchResponse
from app.services.ingestion import (
    IngestionResult,
    SkippedPodcast,
)
from app.core.config import settings

API_KEY = settings.api_key


@dataclass
class FakeITunesClient:
    bulk_response: ITunesSearchResponse | None = None
    single_response: ITunesPodcast | None = None

    async def search_podcasts(
        self,
        term: str = "rock",
        limit: int = 50,
    ) -> ITunesSearchResponse:
        assert term == "rock"
        assert limit == 50

        assert self.bulk_response is not None

        return self.bulk_response

    async def lookup_podcast(
        self,
        collection_id: int,
    ) -> ITunesPodcast | None:
        if self.single_response is None:
            return None

        if self.single_response.collection_id != collection_id:
            return None

        return self.single_response


class FakeIngestionService:
    def __init__(
        self,
        result: IngestionResult,
    ) -> None:
        self.result = result
        self.received: list[ITunesPodcast] = []

    async def ingest(
        self,
        podcasts: list[ITunesPodcast],
    ) -> IngestionResult:
        self.received.extend(podcasts)
        return self.result


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def podcast(
    collection_id: int,
    title: str = "Test Podcast",
) -> ITunesPodcast:
    return ITunesPodcast(
        collectionId=collection_id,
        collectionName=title,
        artistName="Test Author",
        feedUrl="https://example.com/feed.xml",
        collectionViewUrl="https://podcasts.apple.com/test",
        artworkUrl600="https://example.com/image.jpg",
        primaryGenreName="Music",
        genres=["Music"],
        country="USA",
    )


def auth_headers() -> dict[str, str]:
    return {
        "X-API-Key": API_KEY,
    }


def test_bulk_ingestion_requires_api_key(client):
    response = client.post("/ingestion/bulk")

    assert response.status_code == 401
    assert response.json() == {
        "detail": {
            "code": "unauthorized",
            "message": "Invalid or missing API key",
        }
    }


def test_bulk_ingestion_rejects_invalid_api_key(client):
    response = client.post(
        "/ingestion/bulk",
        headers={"X-API-Key": "wrong-key"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": {
            "code": "unauthorized",
            "message": "Invalid or missing API key",
        }
    }


def test_bulk_ingestion_success(client):
    podcasts = [
        podcast(1001, "First Podcast"),
        podcast(1002, "Second Podcast"),
    ]

    fake_client = FakeITunesClient(
        bulk_response=ITunesSearchResponse(
            resultCount=2,
            results=podcasts,
        )
    )

    fake_service = FakeIngestionService(
        IngestionResult(
            fetched=2,
            stored=2,
            skipped=0,
        )
    )

    app.dependency_overrides[get_itunes_client] = (
        lambda: fake_client
    )
    app.dependency_overrides[get_ingestion_service] = (
        lambda: fake_service
    )

    response = client.post(
        "/ingestion/bulk",
        headers=auth_headers(),
    )

    assert response.status_code == 200

    assert response.json() == {
        "fetched": 2,
        "stored": 2,
        "skipped": 0,
        "skipped_items": [],
    }

    assert fake_service.received == podcasts


def test_bulk_ingestion_reports_duplicate_skips(client):
    podcasts = [
        podcast(1001, "New Podcast"),
        podcast(1002, "Existing Podcast"),
    ]

    fake_client = FakeITunesClient(
        bulk_response=ITunesSearchResponse(
            resultCount=2,
            results=podcasts,
        )
    )

    fake_service = FakeIngestionService(
        IngestionResult(
            fetched=2,
            stored=1,
            skipped=1,
            skipped_items=[
                SkippedPodcast(
                    source_id="1002",
                    reason="already_exists",
                )
            ],
        )
    )

    app.dependency_overrides[get_itunes_client] = (
        lambda: fake_client
    )
    app.dependency_overrides[get_ingestion_service] = (
        lambda: fake_service
    )

    response = client.post(
        "/ingestion/bulk",
        headers=auth_headers(),
    )

    assert response.status_code == 200

    assert response.json() == {
        "fetched": 2,
        "stored": 1,
        "skipped": 1,
        "skipped_items": [
            {
                "source_id": "1002",
                "reason": "already_exists",
            }
        ],
    }


def test_single_ingestion_success(client):
    podcast_data = podcast(
        1484275082,
        "Rock Feed",
    )

    fake_client = FakeITunesClient(
        single_response=podcast_data,
    )

    fake_service = FakeIngestionService(
        IngestionResult(
            fetched=1,
            stored=1,
            skipped=0,
        )
    )

    app.dependency_overrides[get_itunes_client] = (
        lambda: fake_client
    )
    app.dependency_overrides[get_ingestion_service] = (
        lambda: fake_service
    )

    response = client.post(
        "/ingestion/single?collection_id=1484275082",
        headers=auth_headers(),
    )

    assert response.status_code == 200

    assert response.json() == {
        "fetched": 1,
        "stored": 1,
        "skipped": 0,
        "skipped_items": [],
    }

    assert fake_service.received == [podcast_data]


def test_single_ingestion_podcast_not_found(client):
    fake_client = FakeITunesClient(
        single_response=None,
    )

    fake_service = FakeIngestionService(
        IngestionResult(),
    )

    app.dependency_overrides[get_itunes_client] = (
        lambda: fake_client
    )
    app.dependency_overrides[get_ingestion_service] = (
        lambda: fake_service
    )

    response = client.post(
        "/ingestion/single?collection_id=999999999",
        headers=auth_headers(),
    )

    assert response.status_code == 200

    assert response.json() == {
        "fetched": 0,
        "stored": 0,
        "skipped": 1,
        "skipped_items": [
            {
                "source_id": "999999999",
                "reason": "Podcast not found",
            }
        ],
    }

    assert fake_service.received == []


def test_single_ingestion_requires_api_key(client):
    response = client.post(
        "/ingestion/single?collection_id=1484275082",
    )

    assert response.status_code == 401


def test_single_ingestion_rejects_invalid_api_key(client):
    response = client.post(
        "/ingestion/single?collection_id=1484275082",
        headers={"X-API-Key": "wrong-key"},
    )

    assert response.status_code == 401


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_bulk_ingest_rejects_empty_term(client):
    response = client.post(
        "/ingestion/bulk?term=",
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["type"] == "string_too_short"
    assert error["loc"] == ["query", "term"]


@pytest.mark.parametrize(
    ("limit", "error_type"),
    [
        ("0", "greater_than_equal"),
        ("-1", "greater_than_equal"),
        ("201", "less_than_equal"),
    ],
)
def test_bulk_ingest_rejects_out_of_range_limit(client, limit, error_type,
):
    response = client.post(
        f"/ingestion/bulk?limit={limit}",
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["type"] == error_type
    assert error["loc"] == ["query", "limit"]


@pytest.mark.parametrize("collection_id", ["0", "-1"])
def test_single_ingest_rejects_non_positive_collection_id(client, collection_id):
    response = client.post(
        f"/ingestion/single?collection_id={collection_id}",
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["type"] == "greater_than"
    assert error["loc"] == ["query", "collection_id"]