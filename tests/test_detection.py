from PIL import Image, ImageDraw

from app.models.schemas import BoundingBox
from app.services.detection import has_high_visibility_signal


def test_high_visibility_signal_detects_yellow_vest_like_crop() -> None:
    image = Image.new("RGB", (120, 120), "black")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 100, 100), fill=(255, 212, 0))
    assert has_high_visibility_signal(image, BoundingBox(xmin=20, ymin=20, xmax=100, ymax=100))


def test_high_visibility_signal_rejects_dark_clothing_crop() -> None:
    image = Image.new("RGB", (120, 120), "black")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 100, 100), fill=(70, 45, 45))
    assert not has_high_visibility_signal(image, BoundingBox(xmin=20, ymin=20, xmax=100, ymax=100))


def test_high_visibility_signal_rejects_small_yellow_object_inside_dark_crop() -> None:
    image = Image.new("RGB", (140, 160), "black")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 120, 150), fill=(60, 45, 45))
    draw.ellipse((78, 104, 102, 128), fill=(255, 212, 0))
    assert not has_high_visibility_signal(image, BoundingBox(xmin=20, ymin=20, xmax=120, ymax=150))
