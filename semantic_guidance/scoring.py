from math import dist

DEFAULT_WEIGHTS = {
    "coordinate": 1.0,
    "category": 20.0,
    "attribute": 5.0,
    "relation": 15.0,
    "scene": 3.0,
}


def box_center(bbox: list[float]) -> tuple[float, float]:
    x, y, w, h = bbox
    return (x + w / 2.0, y + h / 2.0)


def coordinate_score(obj: dict, noisy_point: tuple[float, float]) -> float:
    return -dist(box_center(obj["bbox"]), noisy_point)


def category_score(obj: dict, target_label: str) -> float:
    """Category match: does this object's label match the expected target type?"""
    return 1.0 if obj.get("label") == target_label else 0.0


def attribute_score(obj: dict, target_attributes: list[str]) -> float:
    """Attribute overlap: how many of the target's attributes does this candidate share?"""
    if not target_attributes:
        return 1.0  # no attributes to check → perfect match by default
    candidate_attrs = set(obj.get("attributes", []))
    target_attrs = set(target_attributes)
    return len(candidate_attrs & target_attrs) / len(target_attrs)


def _check_predicate(candidate_center: tuple[float, float],
                     object_center: tuple[float, float],
                     predicate: str) -> bool:
    """Return True if *candidate_center* satisfies *predicate* relative to
    *object_center*.  Supported predicates: left_of, right_of, above, below,
    near (within 200 px)."""
    cx, cy = candidate_center
    ox, oy = object_center
    if predicate == "left_of":
        return cx < ox
    elif predicate == "right_of":
        return cx > ox
    elif predicate == "above":
        return cy < oy  # image coords: y increases downward
    elif predicate == "below":
        return cy > oy
    elif predicate == "near":
        return dist(candidate_center, object_center) < 200.0
    # unknown predicate – skip gracefully
    return True


def relation_score(obj: dict, scene: dict, target_id: str) -> float:
    """Relation consistency: do this candidate's spatial relations match the
    target's?

    For each relation where ``subject_id == target_id`` we check whether the
    candidate's bbox position is consistent with the predicate relative to the
    object_id's bbox.
    """
    relations = scene.get("relations", [])
    relevant = [r for r in relations if r.get("subject_id") == target_id]
    if not relevant:
        return 1.0  # no relations defined → perfect score by default

    # Build an id→object lookup for the scene
    obj_map = {o["id"]: o for o in scene.get("objects", [])}
    candidate_center = box_center(obj["bbox"])

    satisfied = 0
    total = 0
    for rel in relevant:
        ref_obj = obj_map.get(rel.get("object_id"))
        if ref_obj is None:
            continue  # referenced object not found; skip
        total += 1
        ref_center = box_center(ref_obj["bbox"])
        if _check_predicate(candidate_center, ref_center, rel.get("predicate", "")):
            satisfied += 1

    return satisfied / total if total else 1.0


def scene_score(obj: dict, scene_tags: list[str], expected_tags: list[str]) -> float:
    """Scene tag consistency bonus – overlap fraction between actual and
    expected scene tags."""
    if not expected_tags:
        return 1.0
    if not scene_tags:
        return 0.0
    return len(set(scene_tags) & set(expected_tags)) / len(set(expected_tags))


def semantic_score_detailed(
    obj: dict,
    noisy_point: tuple[float, float],
    scene: dict,
    weights: dict[str, float] | None = None,
) -> tuple[float, dict[str, float]]:
    """Compute weighted semantic score with all 5 dimensions.

    Returns ``(total_score, score_breakdown_dict)``.
    """
    w = dict(DEFAULT_WEIGHTS)
    if weights:
        w.update(weights)

    # Identify the target object in the scene to derive expected values
    target_id = scene.get("target_object_id", "")
    target_obj = None
    for o in scene.get("objects", []):
        if o["id"] == target_id:
            target_obj = o
            break

    target_label = target_obj["label"] if target_obj else ""
    target_attributes = target_obj.get("attributes", []) if target_obj else []
    expected_scene_tags = scene.get("scene_tags", [])

    scores = {
        "coordinate": coordinate_score(obj, noisy_point),
        "category": category_score(obj, target_label),
        "attribute": attribute_score(obj, target_attributes),
        "relation": relation_score(obj, scene, target_id),
        "scene": scene_score(obj, scene.get("scene_tags", []), expected_scene_tags),
    }

    total = sum(w[k] * scores[k] for k in scores)
    return total, scores


# ---------------------------------------------------------------------------
# Backward-compatible wrapper used by legacy callers & existing tests
# ---------------------------------------------------------------------------
def semantic_score(
    obj: dict,
    noisy_point: tuple[float, float],
    expected_label: str = "tank",
) -> float:
    """Legacy simplified semantic scoring kept for backward compatibility."""
    score = coordinate_score(obj, noisy_point)
    if obj.get("label") == expected_label:
        score += 20.0
    if obj.get("type") == "target":
        score += 10.0
    if "left" in obj.get("attributes", []):
        score += 2.0
    return score
