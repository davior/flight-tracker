from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, PngImagePlugin


SUPPORTED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png"}
SUPPORTED_IMAGE_FORMATS = {"JPEG", "PNG"}
SUPPORTED_VIDEO_CONTENT_TYPES = {"video/mp4", "video/quicktime", "video/webm"}
VIDEO_EXTENSIONS: dict[str, str] = {
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
}
MAX_DIMENSION = 1600


class ImageStorageError(RuntimeError):
    """Raised when a media file cannot be processed or persisted."""


class UnsupportedImageError(ImageStorageError):
    """Raised when an upload is not a supported image or video type."""


@dataclass(slots=True)
class StoredMedia:
    relative_path: str
    absolute_path: Path
    media_type: str  # "image" or "video"


# Keep backward-compatible alias
StoredImage = StoredMedia


class ImageStorageService:
    def __init__(self, upload_dir: Path):
        self.upload_dir = upload_dir

    async def save_uploads(self, log_id: int, uploads: list) -> list[StoredMedia]:
        target_dir = self.upload_dir / "flight_logs" / str(log_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        stored: list[StoredMedia] = []
        for upload in uploads:
            stored.append(await self._store_single(target_dir, upload))
        return stored

    def cleanup(self, stored: list[StoredMedia]) -> None:
        for item in stored:
            try:
                item.absolute_path.unlink(missing_ok=True)
            except OSError:
                continue

    def delete_files(self, photos: list) -> None:
        """Delete on-disk files for a list of FlightLogPhoto ORM objects."""
        for photo in photos:
            try:
                (self.upload_dir / photo.file_path).unlink(missing_ok=True)
            except OSError:
                continue

    async def _store_single(self, target_dir: Path, upload) -> StoredMedia:
        content_type = upload.content_type or ""

        if content_type in SUPPORTED_VIDEO_CONTENT_TYPES:
            return await self._store_video(target_dir, upload, content_type)

        if content_type in SUPPORTED_IMAGE_CONTENT_TYPES:
            return await self._store_image(target_dir, upload)

        raise UnsupportedImageError(
            "Only JPEG, PNG, MP4, MOV, and WebM uploads are supported"
        )

    async def _store_image(self, target_dir: Path, upload) -> StoredMedia:
        payload = await upload.read()
        try:
            with Image.open(BytesIO(payload)) as image:
                image.load()
                if image.format not in SUPPORTED_IMAGE_FORMATS:
                    raise UnsupportedImageError("Only JPEG and PNG uploads are supported")
                return self._save_processed_image(target_dir, image)
        except UnsupportedImageError:
            raise
        except Exception as exc:
            raise ImageStorageError("Image processing failed") from exc

    async def _store_video(self, target_dir: Path, upload, content_type: str) -> StoredMedia:
        extension = VIDEO_EXTENSIONS[content_type]
        filename = f"{uuid4().hex}{extension}"
        absolute_path = target_dir / filename
        relative_path = str(Path("flight_logs") / target_dir.name / filename)

        payload = await upload.read()
        try:
            absolute_path.write_bytes(payload)
        except OSError as exc:
            raise ImageStorageError("Video storage failed") from exc

        return StoredMedia(
            relative_path=relative_path,
            absolute_path=absolute_path,
            media_type="video",
        )

    def _save_processed_image(self, target_dir: Path, image: Image.Image) -> StoredMedia:
        original_format = image.format or ""
        processed = ImageOps.exif_transpose(image)
        processed.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

        extension = ".jpg" if original_format == "JPEG" else ".png"
        filename = f"{uuid4().hex}{extension}"
        absolute_path = target_dir / filename
        relative_path = str(Path("flight_logs") / target_dir.name / filename)

        save_kwargs = self._build_save_kwargs(processed, image)
        processed.save(absolute_path, format=original_format, **save_kwargs)
        return StoredMedia(
            relative_path=relative_path,
            absolute_path=absolute_path,
            media_type="image",
        )

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
