import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import get_settings
from app.core.exceptions import BadRequestError

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024


class UploadService:
    @staticmethod
    async def save_image(file: UploadFile, store_id: int) -> str:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise BadRequestError("仅支持 JPG/PNG/WebP/GIF 图片")

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise BadRequestError("图片大小不能超过 5MB")

        settings = get_settings()
        filename = f"{uuid.uuid4().hex}{ext}"
        store_dir = Path(settings.storage_local_path) / str(store_id)
        store_dir.mkdir(parents=True, exist_ok=True)
        (store_dir / filename).write_bytes(content)
        return f"/uploads/{store_id}/{filename}"
