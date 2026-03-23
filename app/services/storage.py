from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from PIL import Image

from app.core.config import settings


def save_bytes(content: bytes, suffix: str) -> str:
    filename = f"{uuid4().hex}{suffix}"
    target = settings.artifacts_dir / filename
    target.write_bytes(content)
    return f"/artifacts/{filename}"


def save_image(image: Image.Image, suffix: str = ".png") -> str:
    filename = f"{uuid4().hex}{suffix}"
    target = settings.artifacts_dir / filename
    image.save(target)
    return f"/artifacts/{filename}"


def save_text(text: str, suffix: str = ".md") -> str:
    filename = f"{uuid4().hex}{suffix}"
    target = settings.artifacts_dir / filename
    target.write_text(text, encoding="utf-8")
    return f"/artifacts/{filename}"


def absolute_artifact_path(relative_url: str) -> Path:
    return settings.artifacts_dir / relative_url.replace("/artifacts/", "", 1)
