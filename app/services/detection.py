from __future__ import annotations

import io
import math
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageOps
from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

from app.core.config import settings
from app.models.schemas import BoundingBox, Detection, FrameAnalysis, MediaAsset, SiteSummary, WorkerCompliance
from app.services.compliance import class_aware_nms, evaluate_site, frame_risk_level, keep_best_person_attached_items, normalize_label
from app.services.storage import save_image


TEXT_QUERIES = [
    "person",
    "helmet",
    "hard hat",
    "safety helmet",
    "vest",
    "safety vest",
    "reflective safety vest",
    "reflective vest",
    "high visibility vest",
    "hi vis vest",
    "face mask",
    "gloves",
]

MIN_SCORE_BY_LABEL = {
    "person": 0.28,
    "helmet": 0.36,
    "vest": 0.18,
    "mask": 0.24,
    "gloves": 0.22,
}

COLOR_MAP = {
    "person": "#8B5CF6",
    "helmet": "#22C55E",
    "vest": "#F59E0B",
    "mask": "#06B6D4",
    "gloves": "#EF4444",
}


def clip_box_to_image(box: BoundingBox, image: Image.Image) -> tuple[int, int, int, int]:
    width, height = image.size
    xmin = max(0, min(int(box.xmin), width - 1))
    ymin = max(0, min(int(box.ymin), height - 1))
    xmax = max(xmin + 1, min(int(box.xmax), width))
    ymax = max(ymin + 1, min(int(box.ymax), height))
    return xmin, ymin, xmax, ymax


def has_high_visibility_signal(image: Image.Image, box: BoundingBox) -> bool:
    xmin, ymin, xmax, ymax = clip_box_to_image(box, image)
    crop = image.crop((xmin, ymin, xmax, ymax))
    if crop.width < 8 or crop.height < 8:
        return False

    hsv = cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2HSV)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]

    yellow = (hue >= 18) & (hue <= 42) & (sat >= 80) & (val >= 100)
    orange = (hue >= 5) & (hue <= 18) & (sat >= 90) & (val >= 90)
    reflective = (sat <= 45) & (val >= 180)

    hi_vis_ratio = float((yellow | orange).mean())
    reflective_ratio = float(reflective.mean())
    return hi_vis_ratio >= 0.12 or (hi_vis_ratio >= 0.06 and reflective_ratio >= 0.03)


class PpeDetector:
    def __init__(self) -> None:
        self._processor = None
        self._model = None
        self._device = "cuda" if torch.cuda.is_available() else "cpu"

    def _ensure_model(self) -> None:
        if self._processor is not None and self._model is not None:
            return
        os.environ.setdefault("HF_HOME", settings.hf_cache_dir)
        self._processor = AutoProcessor.from_pretrained(settings.grounding_model_id)
        self._model = AutoModelForZeroShotObjectDetection.from_pretrained(settings.grounding_model_id).to(self._device)
        self._model.eval()

    def detect_image(self, image: Image.Image) -> list[Detection]:
        self._ensure_model()
        prepared = image.convert("RGB")
        inputs = self._processor(images=prepared, text=[TEXT_QUERIES], return_tensors="pt")
        inputs = {key: value.to(self._device) if hasattr(value, "to") else value for key, value in inputs.items()}

        with torch.inference_mode():
            outputs = self._model(**inputs)

        results = self._processor.post_process_grounded_object_detection(
            outputs,
            inputs["input_ids"],
            threshold=settings.detection_threshold,
            text_threshold=0.2,
            target_sizes=[prepared.size[::-1]],
        )

        detections: list[Detection] = []
        for result in results:
            for score, label, box in zip(result["scores"], result["labels"], result["boxes"]):
                canonical_label = normalize_label(str(label))
                if canonical_label not in COLOR_MAP:
                    continue
                confidence = round(float(score), 4)
                if confidence < MIN_SCORE_BY_LABEL.get(canonical_label, settings.detection_threshold):
                    continue
                xmin, ymin, xmax, ymax = [float(value) for value in box.tolist()]
                candidate_box = BoundingBox(xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax)
                if canonical_label == "vest" and not has_high_visibility_signal(prepared, candidate_box):
                    continue
                detections.append(
                    Detection(
                        label=canonical_label,
                        score=confidence,
                        box=candidate_box,
                    )
                )
        detections = class_aware_nms(detections)
        return keep_best_person_attached_items(detections)


detector = PpeDetector()


def annotate_image(image: Image.Image, detections: list[Detection], workers: list[WorkerCompliance]) -> Image.Image:
    canvas = image.convert("RGB").copy()
    draw = ImageDraw.Draw(canvas)

    for detection in detections:
        color = COLOR_MAP.get(detection.label, "#FFFFFF")
        box = detection.box
        draw.rounded_rectangle((box.xmin, box.ymin, box.xmax, box.ymax), outline=color, width=4, radius=12)
        label = f"{detection.label.upper()} {int(detection.score * 100)}%"
        draw.text((box.xmin + 8, max(box.ymin - 22, 8)), label, fill=color)

    for worker in workers:
        color = "#22C55E" if worker.status == "compliant" else "#EF4444"
        label = f"{worker.worker_id} {worker.status.replace('-', ' ').upper()}"
        draw.text((worker.box.xmin + 8, worker.box.ymax + 8), label, fill=color)

    return canvas


def build_storyboard(frames: list[Image.Image]) -> Image.Image:
    thumb_width = 380
    thumb_height = 220
    cols = 2 if len(frames) > 1 else 1
    rows = math.ceil(len(frames) / cols)
    sheet = Image.new("RGB", (cols * thumb_width + 48, rows * thumb_height + 48), "#09101A")

    for index, frame in enumerate(frames):
        thumb = ImageOps.fit(frame, (thumb_width, thumb_height))
        x = 24 + (index % cols) * thumb_width
        y = 24 + (index // cols) * thumb_height
        sheet.paste(thumb, (x, y))
    return sheet


def analyze_image_bytes(payload: bytes, required_items: list[str]) -> tuple[list[Detection], list[WorkerCompliance], SiteSummary, MediaAsset]:
    image = Image.open(io.BytesIO(payload)).convert("RGB")
    detections = detector.detect_image(image)
    workers, summary = evaluate_site(detections, required_items)
    annotated = annotate_image(image, detections, workers)
    url = save_image(annotated, ".png")
    asset = MediaAsset(kind="image", url=url, width=annotated.width, height=annotated.height)
    return detections, workers, summary, asset


def analyze_video_bytes(
    payload: bytes, required_items: list[str]
) -> tuple[list[Detection], list[WorkerCompliance], SiteSummary, MediaAsset, list[FrameAnalysis]]:
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
        temp_file.write(payload)
        temp_path = Path(temp_file.name)

    capture = cv2.VideoCapture(str(temp_path))
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 1.0)
    step = max(1, math.ceil(total_frames / max(settings.max_video_samples, 1)))

    sampled_frames: list[Image.Image] = []
    analyses: list[FrameAnalysis] = []
    all_detections: list[Detection] = []
    last_workers: list[WorkerCompliance] = []
    last_summary: SiteSummary | None = None

    frame_index = 0
    while capture.isOpened():
        success, frame = capture.read()
        if not success:
            break
        if frame_index % step != 0:
            frame_index += 1
            continue

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        detections = detector.detect_image(image)
        workers, summary = evaluate_site(detections, required_items)
        annotated = annotate_image(image, detections, workers)
        thumb_url = save_image(ImageOps.fit(annotated, (720, 420)), ".png")
        analyses.append(
            FrameAnalysis(
                timestamp_seconds=round(frame_index / max(fps, 1.0), 2),
                total_workers=summary.total_workers,
                compliant_workers=summary.compliant_workers,
                non_compliant_workers=summary.non_compliant_workers,
                risk_level=frame_risk_level(summary),
                thumbnail_url=thumb_url,
            )
        )
        sampled_frames.append(annotated)
        all_detections.extend(detections)
        last_workers = workers
        last_summary = summary
        frame_index += 1
        if len(sampled_frames) >= settings.max_video_samples:
            break

    capture.release()
    temp_path.unlink(missing_ok=True)

    if not sampled_frames or last_summary is None:
        raise ValueError("No analyzable frames were found in the uploaded video.")

    storyboard = build_storyboard(sampled_frames)
    asset = MediaAsset(kind="video_storyboard", url=save_image(storyboard, ".png"), width=storyboard.width, height=storyboard.height)
    deduped_detections = class_aware_nms(all_detections, threshold=0.35)
    return deduped_detections, last_workers, last_summary, asset, analyses
