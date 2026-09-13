from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings
from app.schemas.itunes import ITunesSearchResponse, ITunesPodcast


class ITunesClientError(Exception):
    """Raised when the iTunes API cannot be used."""


class ITunesClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 10.0,
        fallback_path: Path | None = None,
    ) -> None:
        self.base_url = base_url or settings.itunes_base_url
        self.timeout = timeout
        self.fallback_path = fallback_path or (
            Path(__file__).resolve().parents[2]
            / "sample_data"
            / "itunes_rock.json"
        )

    async def search_podcasts(
        self,
        term: str = "rock",
        limit: int = 50,
    ) -> ITunesSearchResponse:
        try:
            payload = await self._fetch_from_api(
                term=term,
                limit=limit,
            )
        except (httpx.HTTPError, ITunesClientError):
            payload = self._load_fallback()

        return ITunesSearchResponse.model_validate(payload)

    async def _fetch_from_api(
        self,
        term: str,
        limit: int,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/search"

        params = {
            "media": "podcast",
            "term": term,
            "limit": limit,
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
            ) as client:
                response = await client.get(
                    url,
                    params=params,
                )
        except httpx.RequestError as exc:
            raise ITunesClientError(
                f"Failed to connect to iTunes: {exc}"
            ) from exc

        if response.status_code >= 500:
            raise ITunesClientError(
                f"iTunes server error: {response.status_code}"
            )

        if response.status_code == 429:
            raise ITunesClientError(
                "iTunes rate limit exceeded"
            )

        if response.status_code >= 400:
            raise ITunesClientError(
                f"iTunes request failed: {response.status_code}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ITunesClientError(
                "iTunes returned invalid JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise ITunesClientError(
                "iTunes returned an unexpected response"
            )

        return payload

    def _load_fallback(self) -> dict[str, Any]:
        if not self.fallback_path.exists():
            raise ITunesClientError(
                f"Fallback file not found: {self.fallback_path}"
            )

        try:
            import json

            with self.fallback_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            raise ITunesClientError(
                "Failed to load iTunes fallback data"
            ) from exc

        if not isinstance(payload, dict):
            raise ITunesClientError(
                "iTunes fallback contains an unexpected response"
            )

        return payload

    async def lookup_podcast(self, collection_id: int) -> ITunesPodcast | None:
        try:
            payload = await self._fetch_lookup(collection_id)
        except (httpx.HTTPError, ITunesClientError):
            payload = self._load_fallback()

        response = ITunesSearchResponse.model_validate(payload)

        for podcast in response.results:
            if podcast.collection_id == collection_id:
                return podcast

        return None

    async def _fetch_lookup(
            self,
            collection_id: int,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/lookup"

        params = {
            "id": collection_id,
            "entity": "podcast",
        }

        try:
            async with httpx.AsyncClient(
                    timeout=self.timeout,
            ) as client:
                response = await client.get(
                    url,
                    params=params,
                )
        except httpx.RequestError as exc:
            raise ITunesClientError(
                f"Failed to connect to iTunes: {exc}"
            ) from exc

        if response.status_code >= 500:
            raise ITunesClientError(
                f"iTunes server error: {response.status_code}"
            )

        if response.status_code == 429:
            raise ITunesClientError(
                "iTunes rate limit exceeded"
            )

        if response.status_code >= 400:
            raise ITunesClientError(
                f"iTunes request failed: {response.status_code}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ITunesClientError(
                "iTunes returned invalid JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise ITunesClientError(
                "iTunes returned an unexpected response"
            )

        return payload