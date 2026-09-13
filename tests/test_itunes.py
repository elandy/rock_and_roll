import json
from pathlib import Path

import httpx
import pytest
import respx

from app.services.itunes import ITunesClient


@pytest.fixture
def sample_payload() -> dict:
    path = (
        Path(__file__).resolve().parents[1]
        / "sample_data"
        / "itunes_rock.json"
    )

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


@pytest.mark.asyncio
@respx.mock
async def test_search_podcasts_parses_itunes_response(
    sample_payload: dict,
):
    route = respx.get(
        "https://itunes.apple.com/search"
    ).mock(
        return_value=httpx.Response(
            200,
            json=sample_payload,
        )
    )

    client = ITunesClient()

    result = await client.search_podcasts()

    assert route.called
    assert result.result_count == sample_payload["resultCount"]
    assert len(result.results) == len(
        sample_payload["results"]
    )


@pytest.mark.asyncio
@respx.mock
async def test_search_podcasts_uses_fallback_on_http_error(
    sample_payload: dict,
):
    respx.get(
        "https://itunes.apple.com/search"
    ).mock(
        return_value=httpx.Response(503)
    )

    client = ITunesClient()

    result = await client.search_podcasts()

    assert result.result_count == sample_payload["resultCount"]


@pytest.mark.asyncio
@respx.mock
async def test_search_podcasts_uses_fallback_on_timeout():
    respx.get(
        "https://itunes.apple.com/search"
    ).mock(
        side_effect=httpx.ReadTimeout(
            "request timed out"
        )
    )

    client = ITunesClient()

    result = await client.search_podcasts()

    assert result.result_count > 0


@pytest.mark.asyncio
@respx.mock
async def test_search_podcasts_passes_query_parameters():
    route = respx.get(
        "https://itunes.apple.com/search"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "resultCount": 0,
                "results": [],
            },
        )
    )

    client = ITunesClient()

    result = await client.search_podcasts(
        term="heavy metal",
        limit=25,
    )

    assert result.result_count == 0

    assert route.called
    assert route.calls[0].request.url.params["media"] == "podcast"
    assert route.calls[0].request.url.params["term"] == "heavy metal"
    assert route.calls[0].request.url.params["limit"] == "25"


@pytest.mark.asyncio
@respx.mock
async def test_lookup_podcast_falls_back_to_sample_data_when_upstream_fails():
    collection_id = 813370047

    respx.get("https://itunes.example.com/lookup").mock(
        side_effect=httpx.ConnectError("upstream unavailable")
    )

    client = ITunesClient(
        base_url="https://itunes.example.com",
    )

    podcast = await client.lookup_podcast(collection_id)

    assert podcast is not None
    assert podcast.collection_id == collection_id
    assert podcast.collection_name == "The Purple Rock Survivor Podcast"
    assert podcast.artist_name == "The Purple Rock Survivor Podcast"

@pytest.mark.asyncio
@respx.mock
async def test_lookup_podcast_returns_none_when_id_not_in_sample_data():
    respx.get("https://itunes.example.com/lookup").mock(
        side_effect=httpx.ConnectError("upstream unavailable")
    )

    client = ITunesClient(
        base_url="https://itunes.example.com",
    )

    podcast = await client.lookup_podcast(999999999)

    assert podcast is None