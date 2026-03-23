from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    @property
    def width(self) -> float:
        return max(0.0, self.xmax - self.xmin)

    @property
    def height(self) -> float:
        return max(0.0, self.ymax - self.ymin)


class Detection(BaseModel):
    label: str
    score: float
    box: BoundingBox


class WorkerCompliance(BaseModel):
    worker_id: str
    status: Literal["compliant", "non-compliant"]
    score: float
    required_items: list[str]
    present_items: list[str]
    missing_items: list[str]
    box: BoundingBox


class ExecutiveReport(BaseModel):
    source: Literal["openai", "rules"]
    title: str
    summary: str
    actions: list[str] = Field(default_factory=list)


class MediaAsset(BaseModel):
    kind: Literal["image", "video_storyboard"]
    url: str
    width: int | None = None
    height: int | None = None


class FrameAnalysis(BaseModel):
    timestamp_seconds: float
    total_workers: int
    compliant_workers: int
    non_compliant_workers: int
    risk_level: Literal["low", "medium", "high"]
    thumbnail_url: str


class SiteSummary(BaseModel):
    total_workers: int
    compliant_workers: int
    non_compliant_workers: int
    compliance_rate: float
    detected_items: dict[str, int]
    missing_items: dict[str, int]
    status: Literal["clear", "attention"]


class AnalyzeResponse(BaseModel):
    media_type: Literal["image", "video"]
    filename: str
    required_items: list[str]
    site_summary: SiteSummary
    detections: list[Detection]
    workers: list[WorkerCompliance]
    report: ExecutiveReport
    annotated_asset: MediaAsset
    frames: list[FrameAnalysis] = Field(default_factory=list)
