from dataclasses import dataclass
from html import unescape
from xml.etree import ElementTree

import httpx

from app.utils.html import clean_html


class RSSClientError(Exception):
    """Raised when an RSS feed cannot be fetched or parsed."""


@dataclass(frozen=True)
class RSSMetadata:
    description: str | None
    language: str | None


class RSSClient:
    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    async def fetch_metadata(
        self,
        feed_url: str,
    ) -> RSSMetadata:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
            ) as client:
                response = await client.get(feed_url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RSSClientError(
                f"Failed to fetch RSS feed: {feed_url}"
            ) from exc

        try:
            root = ElementTree.fromstring(response.content)
        except ElementTree.ParseError as exc:
            raise RSSClientError(
                f"RSS feed contains invalid XML: {feed_url}"
            ) from exc

        description = self._find_channel_value(
            root,
            "description",
        )

        language = self._find_channel_value(
            root,
            "language",
        )

        return RSSMetadata(
            description=clean_html(description),
            language=self._clean_text(language),
        )

    @staticmethod
    def _find_channel_value(
        root: ElementTree.Element,
        name: str,
    ) -> str | None:
        channel = root.find("channel")

        if channel is None:
            return None

        element = channel.find(name)

        if element is None:
            return None

        return element.text

    @staticmethod
    def _clean_text(
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = unescape(value)
        value = " ".join(value.split())

        return value or None