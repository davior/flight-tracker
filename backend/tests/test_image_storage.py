from __future__ import annotations

import asyncio
from io import BytesIO

from PIL import Image

from app.services.image_storage import ImageStorageService


class DummyUpload:
    def __init__(self, filename: str, content_type: str, payload: bytes):
        self.filename = filename
        self.content_type = content_type
        self._payload = payload

    async def read(self) -> bytes:
        return self._payload


def create_jpeg_bytes(size: tuple[int, int], exif: bytes | None = None) -> bytes:
    image = Image.new("RGB", size, color="green")
    buffer = BytesIO()
    save_kwargs = {}
    if exif:
        save_kwargs["exif"] = exif
    image.save(buffer, format="JPEG", **save_kwargs)
    return buffer.getvalue()


def test_large_image_is_resized(settings):
    service = ImageStorageService(settings.upload_dir)
    payload = create_jpeg_bytes((3200, 2400))

    saved = asyncio.run(service.save_uploads(1, [DummyUpload("large.jpg", "image/jpeg", payload)]))

    with Image.open(saved[0].absolute_path) as result:
        assert max(result.size) == 1600


def test_small_image_is_not_upscaled(settings):
    service = ImageStorageService(settings.upload_dir)
    payload = create_jpeg_bytes((640, 480))

    saved = asyncio.run(service.save_uploads(1, [DummyUpload("small.jpg", "image/jpeg", payload)]))

    with Image.open(saved[0].absolute_path) as result:
        assert result.size == (640, 480)


def test_jpeg_exif_is_preserved(settings):
    service = ImageStorageService(settings.upload_dir)
    image = Image.new("RGB", (1200, 900), color="red")
    exif = Image.Exif()
    exif[270] = "flight logger"
    buffer = BytesIO()
    image.save(buffer, format="JPEG", exif=exif)

    saved = asyncio.run(
        service.save_uploads(
            2,
            [DummyUpload("with-exif.jpg", "image/jpeg", buffer.getvalue())],
        )
    )

    with Image.open(saved[0].absolute_path) as result:
        assert result.info.get("exif")
        assert result.getexif().get(270) == "flight logger"
