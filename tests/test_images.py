from io import BytesIO
from uuid import uuid4

import httpx
import pytest
import respx
from PIL import Image

from app.services.images import ImageService


IMAGE_URL = "https://example.com/artwork.jpg"


def make_image_bytes() -> bytes:
    image = Image.new(
        "RGB",
        (20, 20),
        (200, 50, 50),
    )

    buffer = BytesIO()
    image.save(buffer, format="JPEG")

    return buffer.getvalue()


@pytest.mark.asyncio
@respx.mock
async def test_process_downloads_image_and_extracts_palette(
    tmp_path,
):
    respx.get(IMAGE_URL).mock(
        return_value=httpx.Response(
            200,
            content=make_image_bytes(),
        )
    )

    podcast_id = uuid4()

    service = ImageService(
        storage_dir=tmp_path,
    )

    result = await service.process(
        IMAGE_URL,
        podcast_id,
    )

    assert result.success is True
    assert result.error is None
    assert result.image_path is not None

    image_path = tmp_path / f"{podcast_id}.jpg"

    assert image_path.exists()
    assert result.image_path == f"images/{podcast_id}.jpg"

    assert result.color_palette
    assert all(
        color.startswith("#")
        for color in result.color_palette
    )


@pytest.mark.asyncio
@respx.mock
async def test_process_handles_http_error(
    tmp_path,
):
    respx.get(IMAGE_URL).mock(
        return_value=httpx.Response(503)
    )

    service = ImageService(
        storage_dir=tmp_path,
    )

    result = await service.process(
        IMAGE_URL,
        uuid4(),
    )

    assert result.success is False
    assert result.image_path is None
    assert result.color_palette == []
    assert result.error is not None

    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
@respx.mock
async def test_process_handles_invalid_image(
    tmp_path,
):
    respx.get(IMAGE_URL).mock(
        return_value=httpx.Response(
            200,
            content=b"this is not an image",
        )
    )

    service = ImageService(
        storage_dir=tmp_path,
    )

    result = await service.process(
        IMAGE_URL,
        uuid4(),
    )

    assert result.success is False
    assert result.image_path is None
    assert result.color_palette == []

    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_process_handles_missing_url(
    tmp_path,
):
    service = ImageService(
        storage_dir=tmp_path,
    )

    result = await service.process(
        None,
        uuid4(),
    )

    assert result.success is False
    assert result.image_path is None
    assert result.color_palette == []
    assert result.error == "No image URL provided"

    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
@respx.mock
async def test_process_handles_empty_response(
    tmp_path,
):
    respx.get(IMAGE_URL).mock(
        return_value=httpx.Response(
            200,
            content=b"",
        )
    )

    service = ImageService(
        storage_dir=tmp_path,
    )

    result = await service.process(
        IMAGE_URL,
        uuid4(),
    )

    assert result.success is False
    assert result.image_path is None
    assert result.color_palette == []


@pytest.mark.asyncio
@respx.mock
async def test_process_follows_redirects(
    tmp_path,
):
    respx.get(IMAGE_URL).mock(
        return_value=httpx.Response(
            200,
            content=make_image_bytes(),
        )
    )

    service = ImageService(
        storage_dir=tmp_path,
    )

    result = await service.process(
        IMAGE_URL,
        uuid4(),
    )

    assert result.success is True