from copy import deepcopy


def default_annotation(image_name: str) -> dict:
    scene_id = image_name.rsplit(".", 1)[0]
    return {
        "image": f"data/images/{image_name}",
        "scene_id": scene_id,
        "scene_tags": [],
        "target_object_id": "",
        "objects": [],
        "relations": [],
        "notes": "",
    }


def validate_annotation(payload: dict) -> None:
    ids = [obj["id"] for obj in payload.get("objects", []) if obj.get("id")]
    if payload.get("target_object_id") and payload["target_object_id"] not in ids:
        raise ValueError("target_object_id must reference an object id")
    if len(ids) != len(set(ids)):
        raise ValueError("object ids must be unique")


def merge_with_default(image_name: str, payload: dict | None) -> dict:
    base = default_annotation(image_name)
    if not payload:
        return base
    merged = deepcopy(base)
    merged.update(payload)
    return merged
