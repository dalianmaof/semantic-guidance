from pathlib import Path

import pytest

from semantic_guidance.annotation_schema import validate_annotation
from semantic_guidance.annotation_store import AnnotationStore


def test_list_images_returns_sorted_pngs(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "b-01.png").write_bytes(b"fake")
    (image_dir / "a-01.png").write_bytes(b"fake")

    store = AnnotationStore(image_dir=image_dir, annotation_dir=tmp_path / "annotations")

    assert store.list_images() == ["a-01.png", "b-01.png"]


def test_save_and_load_annotation_roundtrip(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "a-01.png").write_bytes(b"fake")

    store = AnnotationStore(image_dir=image_dir, annotation_dir=tmp_path / "annotations")
    payload = {
        "image": "data/images/a-01.png",
        "scene_id": "a-01",
        "scene_tags": ["airport"],
        "target_object_id": "tank_1",
        "objects": [{"id": "tank_1", "type": "target", "label": "tank", "bbox": [1, 2, 3, 4], "attributes": []}],
        "relations": [],
        "notes": "",
    }

    store.save_annotation("a-01.png", payload)

    assert store.load_annotation("a-01.png")["target_object_id"] == "tank_1"


def test_load_annotation_returns_default_shape_for_new_image(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "a-01.png").write_bytes(b"fake")

    store = AnnotationStore(image_dir=image_dir, annotation_dir=tmp_path / "annotations")

    annotation = store.load_annotation("a-01.png")

    assert annotation["scene_id"] == "a-01"
    assert annotation["objects"] == []


def test_validate_annotation_rejects_duplicate_object_ids():
    payload = {
        "target_object_id": "tank_1",
        "objects": [
            {"id": "tank_1", "type": "target", "label": "tank", "bbox": [1, 2, 3, 4], "attributes": []},
            {"id": "tank_1", "type": "distractor", "label": "tank", "bbox": [4, 5, 6, 7], "attributes": []},
        ],
        "relations": [],
    }

    with pytest.raises(ValueError):
        validate_annotation(payload)
