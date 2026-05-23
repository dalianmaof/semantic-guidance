from math import dist


def box_center(bbox: list[float]) -> tuple[float, float]:
    x, y, w, h = bbox
    return (x + w / 2.0, y + h / 2.0)


def coordinate_score(obj: dict, noisy_point: tuple[float, float]) -> float:
    return -dist(box_center(obj["bbox"]), noisy_point)


def semantic_score(obj: dict, noisy_point: tuple[float, float], expected_label: str = "tank") -> float:
    score = coordinate_score(obj, noisy_point)
    if obj.get("label") == expected_label:
        score += 20.0
    if obj.get("type") == "target":
        score += 10.0
    if "left" in obj.get("attributes", []):
        score += 2.0
    return score
