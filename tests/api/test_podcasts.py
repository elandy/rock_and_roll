from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.models import Podcast
from app.db.session import get_db
from app.core.config import settings

API_KEY = settings.api_key


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def add_podcast(
    db,
    *,
    title: str,
    category: str = "Rock",
    country: str = "USA",
):
    podcast = Podcast(
        id=uuid4(),
        source="test",
        source_id=title.lower().replace(" ", "-"),
        title=title,
        author="Test Author",
        description="Test description",
        category=category,
        country=country,
        genres=[],
        color_palette=[],
    )
    db.add(podcast)
    db.commit()
    db.refresh(podcast)
    return podcast


def test_get_podcasts_requires_auth(client):
    response = client.get("/podcasts")

    assert response.status_code == 401


def test_get_podcasts_returns_paginated_results(client, db):
    for title in ["Alpha", "Bravo", "Charlie"]:
        add_podcast(db, title=title)

    app.dependency_overrides[get_db] = lambda: db

    response = client.get(
        "/podcasts?page=1&page_size=2",
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert [item["title"] for item in body["items"]] == [
        "Alpha",
        "Bravo",
    ]


def test_get_podcasts_search_filter(client, db):
    add_podcast(db, title="Rock Weekly")
    add_podcast(db, title="Jazz Hour")

    app.dependency_overrides[get_db] = lambda: db

    response = client.get(
        "/podcasts?search=rock",
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 1
    assert body["items"][0]["title"] == "Rock Weekly"


def test_get_podcasts_category_filter(client, db):
    add_podcast(db, title="Rock Show", category="Rock")
    add_podcast(db, title="Jazz Show", category="Jazz")

    app.dependency_overrides[get_db] = lambda: db

    response = client.get(
        "/podcasts?category=rock",
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 1
    assert body["items"][0]["title"] == "Rock Show"


def test_get_podcasts_country_filter(client, db):
    add_podcast(db, title="US Show", country="USA")
    add_podcast(db, title="UK Show", country="UK")

    app.dependency_overrides[get_db] = lambda: db

    response = client.get(
        "/podcasts?country=usa",
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 1
    assert body["items"][0]["title"] == "US Show"


def test_get_podcasts_rejects_invalid_pagination(client):
    response = client.get(
        "/podcasts?page=0&page_size=101",
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 422


def test_get_podcast_requires_auth(client):
    podcast_id = str(uuid4())

    response = client.get(f"/podcasts/{podcast_id}")

    assert response.status_code == 401


def test_get_podcast_returns_podcast(client, db):
    podcast = add_podcast(
        db,
        title="Rock Weekly",
        category="Rock",
        country="USA",
    )

    app.dependency_overrides[get_db] = lambda: db

    response = client.get(
        f"/podcasts/{podcast.id}",
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == str(podcast.id)
    assert body["title"] == "Rock Weekly"
    assert body["author"] == "Test Author"
    assert body["description"] == "Test description"
    assert body["category"] == "Rock"
    assert body["country"] == "USA"
    assert body["genres"] == []
    assert body["color_palette"] == []


def test_get_podcast_returns_404_for_missing_podcast(client, db):
    app.dependency_overrides[get_db] = lambda: db

    podcast_id = uuid4()

    response = client.get(
        f"/podcasts/{podcast_id}",
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": {
            "code": "podcast_not_found",
            "message": "Podcast not found",
        }
    }


def test_get_podcast_rejects_invalid_uuid(client):
    response = client.get(
        "/podcasts/not-a-uuid",
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 422

    error = response.json()["detail"][0]

    assert error["type"] == "uuid_parsing"
    assert error["loc"] == ["path", "podcast_id"]