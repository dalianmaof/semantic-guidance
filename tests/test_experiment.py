from pathlib import Path
import json

from semantic_guidance.experiment import (
    inject_noise,
    load_scenes_from_annotations,
    run_batch_experiment,
    run_single_experiment,
)


def test_inject_noise_is_deterministic_for_seed():
    point = (100.0, 50.0)

    result_a = inject_noise(point, sigma=5.0, seed=7)
    result_b = inject_noise(point, sigma=5.0, seed=7)

    assert result_a == result_b


def test_run_single_experiment_returns_method_outcomes():
    scene = {
        "scene_id": "a-01",
        "target_object_id": "tank_1",
        "objects": [
            {"id": "tank_1", "type": "target", "label": "tank", "bbox": [100, 100, 50, 50], "attributes": ["left"]},
            {"id": "tank_2", "type": "distractor", "label": "tank", "bbox": [160, 100, 50, 50], "attributes": ["right"]},
        ],
        "relations": [],
        "scene_tags": ["airport"],
    }

    result = run_single_experiment(scene, sigma=5.0, seed=3)

    assert set(result["methods"].keys()) == {"coordinate", "semantic"}
    assert result["scene_id"] == "a-01"


def test_run_batch_experiment_writes_csv(tmp_path: Path):
    scenes = [
        {
            "scene_id": "a-01",
            "target_object_id": "tank_1",
            "objects": [
                {"id": "tank_1", "type": "target", "label": "tank", "bbox": [100, 100, 50, 50], "attributes": ["left"]},
                {"id": "tank_2", "type": "distractor", "label": "tank", "bbox": [160, 100, 50, 50], "attributes": ["right"]},
            ],
            "relations": [],
            "scene_tags": ["airport"],
        }
    ]

    output_dir = tmp_path / "results"
    report = run_batch_experiment(scenes, sigmas=[5.0, 15.0], seeds=[1, 2], output_dir=output_dir)

    assert (output_dir / "experiment_rows.csv").exists()
    assert (output_dir / "summary.csv").exists()
    assert report["rows"] == 8


def test_load_scenes_from_annotations_reads_json_files(tmp_path: Path):
    annotation_dir = tmp_path / "annotations"
    annotation_dir.mkdir()
    payload = {
        "image": "data/images/a-01.png",
        "scene_id": "a-01",
        "scene_tags": ["airport"],
        "target_object_id": "tank_1",
        "objects": [{"id": "tank_1", "type": "target", "label": "tank", "bbox": [1, 2, 3, 4], "attributes": []}],
        "relations": [],
        "notes": "",
    }
    (annotation_dir / "a-01.json").write_text(json.dumps(payload), encoding="utf-8")

    scenes = load_scenes_from_annotations(annotation_dir)

    assert len(scenes) == 1
    assert scenes[0]["scene_id"] == "a-01"
