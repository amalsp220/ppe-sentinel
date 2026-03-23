from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


@dataclass(slots=True)
class Settings:
    app_name: str = "PPE Sentinel"
    app_tagline: str = "Industrial-grade PPE compliance intelligence"
    environment: str = os.getenv("APP_ENV", "development")
    host: str = os.getenv("APP_HOST", "0.0.0.0")
    port: int = int(os.getenv("APP_PORT", "7860"))
    detection_threshold: float = float(os.getenv("DETECTION_THRESHOLD", "0.26"))
    max_upload_size_mb: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "60"))
    max_video_samples: int = int(os.getenv("MAX_VIDEO_SAMPLES", "10"))
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.2")
    grounding_model_id: str = os.getenv("GROUNDING_MODEL_ID", "IDEA-Research/grounding-dino-tiny")
    hf_cache_dir: str = os.getenv("HF_HOME", str(BASE_DIR / ".hf-cache"))
    required_items: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            item.strip()
            for item in os.getenv("DEFAULT_REQUIRED_ITEMS", "helmet,vest").split(",")
            if item.strip()
        )
    )
    artifacts_dir: Path = field(default_factory=lambda: BASE_DIR / "artifacts")
    static_dir: Path = field(default_factory=lambda: BASE_DIR / "app" / "static")
    templates_dir: Path = field(default_factory=lambda: BASE_DIR / "app" / "templates")

    def ensure_directories(self) -> None:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        Path(self.hf_cache_dir).mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
