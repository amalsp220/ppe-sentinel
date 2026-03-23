from __future__ import annotations

import re
from collections import Counter

from app.models.schemas import BoundingBox, Detection, SiteSummary, WorkerCompliance


LABEL_ALIASES = {
    "person": "person",
    "worker": "person",
    "helmet": "helmet",
    "hard hat": "helmet",
    "safety helmet": "helmet",
    "hardhat": "helmet",
    "vest": "vest",
    "safety vest": "vest",
    "reflective vest": "vest",
    "high visibility vest": "vest",
    "hi vis vest": "vest",
    "hi-vis vest": "vest",
    "mask": "mask",
    "face mask": "mask",
    "respirator mask": "mask",
    "glove": "gloves",
    "gloves": "gloves",
    "safety gloves": "gloves",
}


def normalize_label(label: str) -> str:
    cleaned = re.sub(r"\s+", " ", label.strip().lower())
    return LABEL_ALIASES.get(cleaned, cleaned)


def center_of(box: BoundingBox) -> tuple[float, float]:
    return ((box.xmin + box.xmax) / 2, (box.ymin + box.ymax) / 2)


def intersection_area(box_a: BoundingBox, box_b: BoundingBox) -> float:
    x_left = max(box_a.xmin, box_b.xmin)
    y_top = max(box_a.ymin, box_b.ymin)
    x_right = min(box_a.xmax, box_b.xmax)
    y_bottom = min(box_a.ymax, box_b.ymax)
    if x_right <= x_left or y_bottom <= y_top:
        return 0.0
    return (x_right - x_left) * (y_bottom - y_top)


def iou(box_a: BoundingBox, box_b: BoundingBox) -> float:
    inter = intersection_area(box_a, box_b)
    union = box_a.width * box_a.height + box_b.width * box_b.height - inter
    if union <= 0:
        return 0.0
    return inter / union


def item_matches_person(item: Detection, person: Detection) -> bool:
    ix, iy = center_of(item.box)
    inside_box = person.box.xmin <= ix <= person.box.xmax and person.box.ymin <= iy <= person.box.ymax
    if not inside_box and intersection_area(item.box, person.box) <= 0:
        return False

    height = max(person.box.height, 1.0)
    rel_y = (iy - person.box.ymin) / height

    if item.label == "helmet":
        return rel_y <= 0.42
    if item.label == "mask":
        return rel_y <= 0.5
    if item.label == "vest":
        return 0.18 <= rel_y <= 0.88
    if item.label == "gloves":
        return 0.2 <= rel_y <= 1.02
    return True


def class_aware_nms(detections: list[Detection], threshold: float = 0.45) -> list[Detection]:
    grouped: dict[str, list[Detection]] = {}
    for detection in detections:
        grouped.setdefault(detection.label, []).append(detection)

    final: list[Detection] = []
    for group in grouped.values():
        kept: list[Detection] = []
        for detection in sorted(group, key=lambda item: item.score, reverse=True):
            if any(iou(detection.box, existing.box) >= threshold for existing in kept):
                continue
            kept.append(detection)
        final.extend(kept)
    return final


def evaluate_site(detections: list[Detection], required_items: list[str]) -> tuple[list[WorkerCompliance], SiteSummary]:
    canonical_required = [normalize_label(item) for item in required_items]
    people = [item for item in detections if item.label == "person"]
    workers: list[WorkerCompliance] = []
    detected_counter: Counter[str] = Counter()
    missing_counter: Counter[str] = Counter()

    for item in detections:
        if item.label != "person":
            detected_counter[item.label] += 1

    for index, person in enumerate(sorted(people, key=lambda item: item.box.xmin), start=1):
        attached_items = {
            item.label
            for item in detections
            if item.label != "person" and item_matches_person(item, person)
        }
        missing_items = [item for item in canonical_required if item not in attached_items]
        for missing in missing_items:
            missing_counter[missing] += 1

        present_items = [item for item in canonical_required if item in attached_items]
        score = 100.0 if not canonical_required else round((len(present_items) / len(canonical_required)) * 100, 1)
        workers.append(
            WorkerCompliance(
                worker_id=f"W-{index:02d}",
                status="compliant" if not missing_items else "non-compliant",
                score=score,
                required_items=canonical_required,
                present_items=present_items,
                missing_items=missing_items,
                box=person.box,
            )
        )

    compliant_workers = sum(1 for worker in workers if worker.status == "compliant")
    total_workers = len(workers)
    compliance_rate = round((compliant_workers / total_workers) * 100, 1) if total_workers else 0.0
    summary = SiteSummary(
        total_workers=total_workers,
        compliant_workers=compliant_workers,
        non_compliant_workers=max(total_workers - compliant_workers, 0),
        compliance_rate=compliance_rate,
        detected_items=dict(sorted(detected_counter.items())),
        missing_items=dict(sorted(missing_counter.items())),
        status="clear" if total_workers and compliant_workers == total_workers else "attention",
    )
    return workers, summary


def frame_risk_level(summary: SiteSummary) -> str:
    if summary.non_compliant_workers == 0:
        return "low"
    if summary.compliance_rate >= 60:
        return "medium"
    return "high"
