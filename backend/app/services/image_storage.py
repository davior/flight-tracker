from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, PngImagePlugin


SUPPORTED_CONTENT_TYPES = {"image/jpeg", "image/png"}
SUPPORTED_FORMATS = {"JPEG", "PNG"}
MAX_DIMENSION = 1600


class ImageStorageError(RuntimeError):
    """Raised when an image cannot be processed or persisted."""


class UnsupportedImageError(ImageStorageError):
    """Raised when an upload is not a supported image type."""


@dataclass(slots=True)
class StoredImage:
    relative_path: str
    absolute_path: Path


class ImageStorageService:
    def __init__(self, upload_dir: Path):
        self.upload_dir = upload_dir

    async def save_uploads(self, log_id: int, uploads: list) -> list[StoredImage]:
        target_dir = self.upload_dir / "flight_logs" / str(log_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        stored_images: list[StoredImage] = []
        for upload in uploads:
            stored_images.append(await self._store_single(target_dir, upload))
        return stored_images

    def cleanup(self, stored_images: list[StoredImage]) -> None:
        for item in stored_images:
            try:
                item.absolute_path.unlink(missing_ok=True)
            except OSError:
                continue

    async def _store_single(self, target_dir: Path, upload) -> StoredImage:
        if upload.content_type not in SUPPORTED_CONTENT_TYPES:
            raise UnsupportedImageError("Only JPEG and PNG uploads are supported")

        payload = await upload.read()
        try:
            with Image.open(BytesIO(payload)) as image:
                image.load()
                if image.format not in SUPPORTED_FORMATS:
                    raise UnsupportedImageError("Only JPEG and PNG uploads are supported")
                return self._save_processed_image(target_dir, image)
        except UnsupportedImageError:
            raise
        except Exception as exc:
            raise ImageStorageError("Image processing failed") from exc

    def _save_processed_image(self, target_dir: Path, image: Image.Image) -> StoredImage:
        original_format = image.format or ""
        processed = ImageOps.exif_transpose(image)
        processed.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

        extension = ".jpg" if original_format == "JPEG" else ".png"
        filename = f"{uuid4().hex}{extension}"
        absolute_path = target_dir / filename
        relative_path = str(Path("flight_logs") / target_dir.name / filename)

        save_kwargs = self._build_save_kwargs(processed, image)
        processed.save(absolute_path, format=original_format, **save_kwargs)
        return StoredImage(relative_path=relative_path, absolute_path=absolute_path)

    def _build_save_kwargs(self, processed: Image.Image, original: Image.Image) -> dict[str, object]:
        if original.format == "JPEG":
            save_kwargs: dict[str, object] = {"quality": 90, "optimize": True}
            exif = processed.getexif()
            exif_bytes = exif.tobytes() if exif else None
            if exif_bytes:
                save_kwargs["exif"] = exif_bytes
            icc_profile = original.info.get("icc_profile")
            if icc_profile:
                save_kwargs["icc_profile"] = icc_profile
            return save_kwargs

        save_kwargs = {"optimize": True}
        pnginfo = PngImagePlugin.PngInfo()
        has_text_chunks = False
        for key, value in original.info.items():
            if isinstance(value, str):
                pnginfo.add_text(key, value)
                has_text_chunks = True

        if has_text_chunks:
            save_kwargs["pnginfo"] = pnginfo

        exif = original.info.get("exif")
        if exif:
            save_kwargs["exif"] = exif

        icc_profile = original.info.get("icc_profile")
        if icc_profile:
            save_kwargs["icc_profile"] = icc_profile

        return save_kwargs
