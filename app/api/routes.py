from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.models.schemas import AnalyzeResponse
from app.services.detection import analyze_image_bytes, analyze_video_bytes
from app.services.reporting import build_openai_report, build_rule_based_report


router = APIRouter()
templates = Jinja2Templates(directory=str(settings.templates_dir))

IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_TYPES = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def parse_required_items(value: str | None) -> list[str]:
    if not value:
        return list(settings.required_items)
    items = [item.strip().lower() for item in value.split(",") if item.strip()]
    return items or list(settings.required_items)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.app_name,
            "tagline": settings.app_tagline,
            "default_required_items": list(settings.required_items),
            "openai_enabled": bool(settings.openai_api_key),
        },
    )


@router.get("/health")
async def health() -> JSONResponse:
    return JSONResponse(
        {"status": "ok", "model": settings.grounding_model_id, "openai_enabled": bool(settings.openai_api_key)}
    )


@router.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(...),
    required_items: str = Form(""),
    generate_ai_summary: bool = Form(True),
) -> AnalyzeResponse:
    suffix = Path(file.filename or "upload.bin").suffix.lower()
    if suffix not in IMAGE_TYPES | VIDEO_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload an image or a short video.")

    payload = await file.read()
    if len(payload) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.max_upload_size_mb} MB upload limit.")

    chosen_required_items = parse_required_items(required_items)
    filename = file.filename or "upload"

    try:
        if suffix in IMAGE_TYPES:
            detections, workers, site_summary, annotated_asset = analyze_image_bytes(payload, chosen_required_items)
            media_type = "image"
            frames = []
        else:
            detections, workers, site_summary, annotated_asset, frames = analyze_video_bytes(payload, chosen_required_items)
            media_type = "video"
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    report = (
        build_openai_report(filename, media_type, site_summary, workers, chosen_required_items)
        if generate_ai_summary
        else build_rule_based_report(filename, media_type, site_summary, workers, chosen_required_items)
    )

    return AnalyzeResponse(
        media_type=media_type,
        filename=filename,
        required_items=chosen_required_items,
        site_summary=site_summary,
        detections=detections,
        workers=workers,
        report=report,
        annotated_asset=annotated_asset,
        frames=frames,
    )
