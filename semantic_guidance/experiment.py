import json
import random
from pathlib import Path

from semantic_guidance.reporting import write_chart, write_rows, write_summary
from semantic_guidance.scoring import coordinate_score, semantic_score


def inject_noise(point: tuple[float, float], sigma: float, seed: int) -> tuple[float, float]:
    rng = random.Random(seed)
    return (
        point[0] + rng.gauss(0.0, sigma),
        point[1] + rng.gauss(0.0, sigma),
    )


def choose_best(scene: dict, noisy_point: tuple[float, float], method: str) -> dict | None:
    candidates = [obj for obj in scene.get("objects", []) if obj.get("type") in {"target", "distractor"}]
    if not candidates:
        return None
    scorer = coordinate_score if method == "coordinate" else semantic_score
    return max(candidates, key=lambda obj: scorer(obj, noisy_point))


def run_single_experiment(scene: dict, sigma: float, seed: int) -> dict:
    target = next(obj for obj in scene["objects"] if obj["id"] == scene["target_object_id"])
    x, y, w, h = target["bbox"]
    target_center = (x + w / 2.0, y + h / 2.0)
    noisy_point = inject_noise(target_center, sigma=sigma, seed=seed)

    methods = {}
    for method_name in ("coordinate", "semantic"):
        chosen = choose_best(scene, noisy_point, method_name)
        methods[method_name] = {
            "selected_id": chosen["id"] if chosen else "",
            "success": bool(chosen and chosen["id"] == scene["target_object_id"]),
        }

    return {
        "scene_id": scene["scene_id"],
        "sigma": sigma,
        "seed": seed,
        "noisy_point": noisy_point,
        "methods": methods,
    }


def run_batch_experiment(scenes: list[dict], sigmas: list[float], seeds: list[int], output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for scene in scenes:
        for sigma in sigmas:
            for seed in seeds:
                result = run_single_experiment(scene, sigma=sigma, seed=seed)
                for method, details in result["methods"].items():
                    rows.append(
                        {
                            "scene_id": result["scene_id"],
                            "sigma": sigma,
                            "seed": seed,
                            "method": method,
                            "selected_id": details["selected_id"],
                            "success": details["success"],
                        }
                    )
    write_rows(output_dir / "experiment_rows.csv", rows)
    summary = write_summary(output_dir / "summary.csv", rows)
    write_chart(output_dir / "success_rate.png", summary)
    return {"rows": len(rows), "summary": summary}


def load_scenes_from_annotations(annotation_dir: Path) -> list[dict]:
    scenes = []
    for path in sorted(annotation_dir.glob("*.json")):
        scenes.append(json.loads(path.read_text(encoding="utf-8")))
    return scenes
