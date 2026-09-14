from uuid import uuid4
import json
import pytest
from fastapi.testclient import TestClient
import os

from app.db.models import Podcast
from app.db.session import get_db
from app.main import app
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
        genres=["Rock"],
        color_palette=["#111111", "#FFFFFF"],
    )
    db.add(podcast)
    db.commit()
    db.refresh(podcast)
    return podcast


def test_export_podcasts_requires_auth(client):
    response = client.get("/export/podcasts")

    assert response.status_code == 401


def test_export_podcasts_returns_ndjson(client, db):
    first = add_podcast(db, title="First Podcast")
    second = add_podcast(db, title="Second Podcast")

    app.dependency_overrides[get_db] = lambda: db

    response = client.get(
        "/export/podcasts",
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/x-ndjson"
    )
    data = [
        json.loads(line)
        for line in response.content.decode("utf-8").splitlines()
    ]

    assert len(data) == 2

    by_id = {item["id"]: item for item in data}

    assert str(first.id) in by_id
    assert str(second.id) in by_id

    assert by_id[str(first.id)]["title"] == "First Podcast"
    assert by_id[str(second.id)]["title"] == "Second Podcast"


def test_export_podcasts_returns_empty_stream(client, db):
    app.dependency_overrides[get_db] = lambda: db

    response = client.get(
        "/export/podcasts",
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/x-ndjson"
    )
    assert response.content == b""