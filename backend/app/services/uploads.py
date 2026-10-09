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
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    # Allow slightly larger camera originals; we recompress to JPEG below.
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="图片过大（超过 20MB），请压缩后再传",
        )

    try:
        img = Image.open(BytesIO(raw))
        img.load()
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法识别图片格式（iPhone 请用相册导出 JPG，或在 App 内由浏览器转换后再传）",
        ) from exc

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
    quality = 85
    img.save(dest, format="JPEG", quality=quality, optimize=True)
    while dest.stat().st_size > MAX_MEAL_IMAGE_BYTES and quality > 50:
        quality -= 10
        img.save(dest, format="JPEG", quality=quality, optimize=True)

    return f"{user_id}/{filename}"
