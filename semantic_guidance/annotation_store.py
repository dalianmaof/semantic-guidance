import json
from pathlib import Path

from semantic_guidance.annotation_schema import merge_with_default, validate_annotation


class AnnotationStore:
    def __init__(self, image_dir: Path, annotation_dir: Path) -> None:
        self.image_dir = Path(image_dir)
        self.annotation_dir = Path(annotation_dir)
        self.annotation_dir.mkdir(parents=True, exist_ok=True)

    def list_images(self) -> list[str]:
        return sorted(path.name for path in self.image_dir.glob("*.png"))

    def annotation_path(self, image_name: str) -> Path:
        stem = Path(image_name).stem
        return self.annotation_dir / f"{stem}.json"

    def load_annotation(self, image_name: str) -> dict:
        path = self.annotation_path(image_name)
        if not path.exists():
            return merge_with_default(image_name, None)
        return merge_with_default(image_name, json.loads(path.read_text(encoding="utf-8")))

    def save_annotation(self, image_name: str, payload: dict) -> None:
        validate_annotation(payload)
        path = self.annotation_path(image_name)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
