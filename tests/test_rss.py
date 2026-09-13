import httpx
import pytest
import respx

from app.services.rss import RSSClient, RSSClientError


RSS_URL = "https://example.com/feed.xml"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_metadata():
    respx.get(RSS_URL).mock(
        return_value=httpx.Response(
            200,
            content=b"""
                <rss version="2.0">
                    <channel>
                        <title>Rock Feed</title>
                        <description>
                            <![CDATA[
                                <p>The <strong>best</strong> rock podcast.</p>
                            ]]>
                        </description>
                        <language>en-us</language>
                    </channel>
                </rss>
            """,
        )
    )

    client = RSSClient()

    result = await client.fetch_metadata(RSS_URL)

    assert result.description == "The best rock podcast."
    assert result.language == "en-us"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_metadata_handles_missing_fields():
    respx.get(RSS_URL).mock(
        return_value=httpx.Response(
            200,
            content=b"""
                <rss version="2.0">
                    <channel>
                        <title>Rock Feed</title>
                    </channel>
                </rss>
            """,
        )
    )

    client = RSSClient()

    result = await client.fetch_metadata(RSS_URL)

    assert result.description is None
    assert result.language is None


@pytest.mark.asyncio
@respx.mock
async def test_fetch_metadata_raises_on_http_error():
    respx.get(RSS_URL).mock(
        return_value=httpx.Response(503)
    )

    client = RSSClient()

    with pytest.raises(RSSClientError):
        await client.fetch_metadata(RSS_URL)


@pytest.mark.asyncio
@respx.mock
async def test_fetch_metadata_raises_on_invalid_xml():
    respx.get(RSS_URL).mock(
        return_value=httpx.Response(
            200,
            content=b"not valid xml",
        )
    )

    client = RSSClient()

    with pytest.raises(RSSClientError):
        await client.fetch_metadata(RSS_URL)


@pytest.mark.asyncio
@respx.mock
async def test_fetch_metadata_follows_redirects():
    respx.get(RSS_URL).mock(
        return_value=httpx.Response(
            200,
            content=b"""
                <rss version="2.0">
                    <channel>
                        <description>Rock podcast</description>
                    </channel>
                </rss>
            """,
        )
    )

    client = RSSClient()

    result = await client.fetch_metadata(RSS_URL)

    assert result.description == "Rock podcast"
