from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image

from backend.app.settings import ROOT, get_settings

MAX_MEAL_IMAGE_BYTES = 5 * 1024 * 1024
MAX_MEAL_IMAGE_EDGE = 1280


def meal_upload_root() -> Path:
    settings = get_settings()
    root = Path(settings.upload_dir)
    if not root.is_absolute():
        root = ROOT / root
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_meal_image(file: UploadFile, user_id: str) -> str:
    raw = file.file.read()
    if len(raw) > MAX_MEAL_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image must be at most 5MB",
        )
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    try:
        img = Image.open(BytesIO(raw))
        img.load()
    except OSError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image") from exc

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    w, h = img.size
    longest = max(w, h)
    if longest > MAX_MEAL_IMAGE_EDGE:
        scale = MAX_MEAL_IMAGE_EDGE / longest
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    user_dir = meal_upload_root() / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.jpg"
    dest = user_dir / filename
    img.save(dest, format="JPEG", quality=85, optimize=True)

    return f"{user_id}/{filename}"
