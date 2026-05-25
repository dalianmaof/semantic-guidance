import json
import random
from pathlib import Path

from semantic_guidance.reporting import write_chart, write_rows, write_summary
from semantic_guidance.scoring import (
    coordinate_score,
    semantic_score,
    semantic_score_detailed,
)


def inject_noise(point: tuple[float, float], sigma: float, seed: int) -> tuple[float, float]:
    rng = random.Random(seed)
    return (
        point[0] + rng.gauss(0.0, sigma),
        point[1] + rng.gauss(0.0, sigma),
    )


def choose_best(
    scene: dict,
    noisy_point: tuple[float, float],
    method: str,
    weights: dict[str, float] | None = None,
) -> tuple[dict | None, dict[str, float] | None]:
    """Select the best candidate from *scene* using *method*.

    Returns ``(chosen_object, score_breakdown)`` where *score_breakdown* is a
    dict of per-dimension scores (only for the ``"semantic"`` method, ``None``
    for ``"coordinate"``).
    """
    candidates = [obj for obj in scene.get("objects", []) if obj.get("type") in {"target", "distractor"}]
    if not candidates:
        return None, None

    if method == "coordinate":
        best = max(candidates, key=lambda obj: coordinate_score(obj, noisy_point))
        return best, None

    # semantic method – use full 5-dimension scoring
    best_obj = None
    best_total = float("-inf")
    best_breakdown = None
    for obj in candidates:
        total, breakdown = semantic_score_detailed(obj, noisy_point, scene, weights=weights)
        if total > best_total:
            best_total = total
            best_obj = obj
            best_breakdown = breakdown
    return best_obj, best_breakdown


def run_single_experiment(
    scene: dict,
    sigma: float,
    seed: int,
    weights: dict[str, float] | None = None,
) -> dict:
    target = next(obj for obj in scene["objects"] if obj["id"] == scene["target_object_id"])
    
    # Locate annotated distractors and dynamically shift them close to the target
    # to simulate a challenging close-range tactical interference scenario using actual annotations
    simulated_objects = []
    has_distractor = False
    for obj in scene["objects"]:
        if obj.get("type") == "distractor":
            has_distractor = True
            # Shift the actual annotated distractor close to the target
            shifted_obj = {
                **obj,
                "bbox": [
                    target["bbox"][0] + 120,
                    target["bbox"][1] + 60,
                    obj["bbox"][2] if len(obj["bbox"]) > 2 else 50,
                    obj["bbox"][3] if len(obj["bbox"]) > 3 else 50,
                ] if isinstance(obj["bbox"], list) else obj["bbox"]
            }
            simulated_objects.append(shifted_obj)
        else:
            simulated_objects.append(obj)
            
    # Fallback: if the scene has no annotated distractor, dynamically generate a same-type close decoy
    if not has_distractor:
        decoy_id = f"{target['id']}_decoy"
        decoy = {
            "id": decoy_id,
            "type": "distractor",
            "label": target["label"],
            "bbox": [
                target["bbox"][0] + 120,
                target["bbox"][1] + 60,
                target["bbox"][2],
                target["bbox"][3]
            ],
            "attributes": ["decoy", "inactive"],
        }
        simulated_objects.append(decoy)
        
    sim_scene = {
        **scene,
        "objects": simulated_objects
    }
    
    x, y, w, h = target["bbox"]
    target_center = (x + w / 2.0, y + h / 2.0)
    noisy_point = inject_noise(target_center, sigma=sigma, seed=seed)

    methods = {}
    for method_name in ("coordinate", "semantic"):
        chosen, breakdown = choose_best(sim_scene, noisy_point, method_name, weights=weights)
        entry: dict = {
            "selected_id": chosen["id"] if chosen else "",
            "success": bool(chosen and chosen["id"] == scene["target_object_id"]),
        }
        if breakdown is not None:
            entry["score_breakdown"] = breakdown
        methods[method_name] = entry

    return {
        "scene_id": scene["scene_id"],
        "sigma": sigma,
        "seed": seed,
        "noisy_point": noisy_point,
        "methods": methods,
    }


def run_batch_experiment(
    scenes: list[dict],
    sigmas: list[float],
    seeds: list[int],
    output_dir: Path,
    weights: dict[str, float] | None = None,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for scene in scenes:
        for sigma in sigmas:
            for seed in seeds:
                result = run_single_experiment(scene, sigma=sigma, seed=seed, weights=weights)
                for method, details in result["methods"].items():
                    row = {
                        "scene_id": result["scene_id"],
                        "sigma": sigma,
                        "seed": seed,
                        "method": method,
                        "selected_id": details["selected_id"],
                        "success": details["success"],
                    }
                    # Flatten score breakdown into columns if present
                    if "score_breakdown" in details:
                        for dim, val in details["score_breakdown"].items():
                            row[f"score_{dim}"] = val
                    rows.append(row)

    write_rows(output_dir / "experiment_rows.csv", rows)
    summary = write_summary(output_dir / "summary.csv", rows)
    write_chart(output_dir / "success_rate.png", summary)
    return {"rows": len(rows), "summary": summary}


def load_scenes_from_annotations(annotation_dir: Path) -> list[dict]:
    scenes = []
    for path in sorted(annotation_dir.glob("*.json")):
        scenes.append(json.loads(path.read_text(encoding="utf-8")))
    return scenes
