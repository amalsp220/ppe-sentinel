from app.models.schemas import BoundingBox, Detection
from app.services.compliance import evaluate_site, keep_best_person_attached_items, normalize_label


def make_detection(label: str, xmin: float, ymin: float, xmax: float, ymax: float, score: float = 0.9) -> Detection:
    return Detection(label=label, score=score, box=BoundingBox(xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax))


def test_normalize_label_maps_aliases() -> None:
    assert normalize_label("hard hat") == "helmet"
    assert normalize_label("reflective vest") == "vest"
    assert normalize_label("yellow safety jacket") == "vest"


def test_site_evaluation_marks_compliant_worker() -> None:
    detections = [
        make_detection("person", 0, 0, 100, 220),
        make_detection("helmet", 20, 0, 75, 45),
        make_detection("vest", 15, 55, 85, 180),
    ]
    workers, summary = evaluate_site(detections, ["helmet", "vest"])
    assert summary.compliance_rate == 100.0
    assert workers[0].status == "compliant"


def test_site_evaluation_marks_missing_item() -> None:
    detections = [
        make_detection("person", 0, 0, 100, 220),
        make_detection("helmet", 20, 0, 75, 45),
    ]
    workers, summary = evaluate_site(detections, ["helmet", "vest"])
    assert summary.non_compliant_workers == 1
    assert workers[0].missing_items == ["vest"]


def test_keep_best_person_attached_items_filters_bad_helmet() -> None:
    detections = [
        make_detection("person", 0, 0, 100, 220),
        make_detection("helmet", 85, 10, 98, 40, score=0.7),
        make_detection("vest", 20, 60, 85, 180, score=0.8),
    ]
    filtered = keep_best_person_attached_items(detections)
    labels = [item.label for item in filtered]
    assert labels.count("person") == 1
    assert labels.count("vest") == 1
    assert labels.count("helmet") == 0
