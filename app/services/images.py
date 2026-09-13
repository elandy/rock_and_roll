from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import colorgram
import httpx
from PIL import Image, UnidentifiedImageError


@dataclass(frozen=True)
class ImageProcessingResult:
    success: bool
    image_path: str | None
    color_palette: list[str]
    error: str | None = None


class ImageService:
    def __init__(
        self,
        storage_dir: Path,
        timeout: float = 10.0,
        palette_size: int = 5,
    ) -> None:
        self.storage_dir = storage_dir
        self.timeout = timeout
        self.palette_size = palette_size

    async def process(
        self,
        image_url: str | None,
        podcast_id: UUID,
    ) -> ImageProcessingResult:
        if not image_url:
            return ImageProcessingResult(
                success=False,
                image_path=None,
                color_palette=[],
                error="No image URL provided",
            )

        self.storage_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination = self.storage_dir / f"{podcast_id}.jpg"

        try:
            image_bytes = await self._download(image_url)

            destination.write_bytes(image_bytes)

            self._validate_image(destination)

            palette = self._extract_palette(destination)
            relative_path = Path("images") / destination.name

            return ImageProcessingResult(
                success=True,
                image_path=str(relative_path),
                color_palette=palette,
            )

        except (httpx.HTTPError, OSError, UnidentifiedImageError, ValueError) as exc:
            self._remove_file(destination)

            return ImageProcessingResult(
                success=False,
                image_path=None,
                color_palette=[],
                error=str(exc),
            )

    async def _download(
        self,
        image_url: str,
    ) -> bytes:
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            response = await client.get(image_url)
            response.raise_for_status()

        if not response.content:
            raise ValueError("Image response was empty")

        return response.content

    @staticmethod
    def _validate_image(path: Path) -> None:
        try:
            with Image.open(path) as image:
                image.verify()
        except UnidentifiedImageError:
            raise
        except OSError as exc:
            raise ValueError(
                "Downloaded file is not a valid image"
            ) from exc

    def _extract_palette(
        self,
        path: Path,
    ) -> list[str]:
        colors = colorgram.extract(
            str(path),
            self.palette_size,
        )

        return [
            self._rgb_to_hex(color.rgb)
            for color in colors
        ]

    @staticmethod
    def _rgb_to_hex(
        rgb: tuple[int, int, int],
    ) -> str:
        red, green, blue = rgb

        return f"#{red:02X}{green:02X}{blue:02X}"

    @staticmethod
    def _remove_file(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass