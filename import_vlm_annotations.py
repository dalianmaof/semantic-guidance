import os
import json
from pathlib import Path
from PIL import Image
from semantic_guidance.annotation_schema import validate_annotation

def scale_box(box_1000: list[float], img_w: int, img_h: int) -> list[int]:
    """Convert normalized [x, y, w, h] in 0-1000 range to absolute pixel coordinates."""
    x_norm, y_norm, w_norm, h_norm = box_1000
    x = int(round((x_norm / 1000.0) * img_w))
    y = int(round((y_norm / 1000.0) * img_h))
    w = int(round((w_norm / 1000.0) * img_w))
    h = int(round((h_norm / 1000.0) * img_h))
    
    # Clip to image boundaries
    x = max(0, min(x, img_w - 1))
    y = max(0, min(y, img_h - 1))
    w = max(1, min(w, img_w - x))
    h = max(1, min(h, img_h - y))
    
    return [x, y, w, h]

def process_vlm_annotation(vlm_json_path: Path, images_dir: Path, annotations_dir: Path) -> dict:
    print(f"Processing VLM annotation: {vlm_json_path.name}")
    
    with open(vlm_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Get image filename from JSON or use same name as JSON
    image_name = data.get("image_name")
    if not image_name:
        # Fallback to matching image stem
        stem = vlm_json_path.stem
        # Find matching image in images_dir
        matches = list(images_dir.glob(f"{stem}.*"))
        if matches:
            image_name = matches[0].name
        else:
            raise FileNotFoundError(f"Could not find matching image for {vlm_json_path.name} in {images_dir}")
            
    img_path = images_dir / image_name
    if not img_path.exists():
        raise FileNotFoundError(f"Image not found: {img_path}")
        
    # Open image to get natural dimensions
    with Image.open(img_path) as img:
        img_w, img_h = img.size
        
    print(f"  Image size: {img_w}x{img_h}")
    
    # Reconstruct standard annotation structure
    scene_id = vlm_json_path.stem
    standardized = {
        "image": f"data/images/{image_name}",
        "scene_id": scene_id,
        "scene_tags": data.get("scene_tags", []),
        "target_object_id": data.get("target_object_id", ""),
        "objects": [],
        "relations": [],
        "notes": data.get("notes", "VLM Auto-Generated")
    }
    
    # Scale objects bboxes
    for obj in data.get("objects", []):
        bbox_1000 = obj.get("bbox")
        if not bbox_1000 or len(bbox_1000) != 4:
            print(f"  [Warning] Invalid bbox for object {obj.get('id')}: {bbox_1000}. Skipping.")
            continue
            
        scaled_bbox = scale_box(bbox_1000, img_w, img_h)
        
        standardized["objects"].append({
            "id": obj.get("id"),
            "type": obj.get("type", "target"),
            "label": obj.get("label", ""),
            "bbox": scaled_bbox,
            "attributes": obj.get("attributes", [])
        })
        
    # Copy relations
    for rel in data.get("relations", []):
        standardized["relations"].append({
            "subject_id": rel.get("subject_id"),
            "predicate": rel.get("predicate"),
            "object_id": rel.get("object_id")
        })
        
    # Validate structure
    try:
        validate_annotation(standardized)
    except ValueError as e:
        print(f"  [Error] Validation failed: {e}")
        raise e
        
    # Save standard annotation
    dest_path = annotations_dir / f"{scene_id}.json"
    with open(dest_path, "w", encoding="utf-8") as f:
        json.dump(standardized, f, ensure_ascii=False, indent=2)
        
    print(f"  [Success] Saved to {dest_path.relative_to(dest_path.parents[2])}")
    return standardized

def main():
    base_dir = Path(__file__).resolve().parent
    vlm_dir = base_dir / "data" / "vlm_outputs"
    images_dir = base_dir / "data" / "images"
    annotations_dir = base_dir / "data" / "annotations"
    
    # Ensure directories exist
    vlm_dir.mkdir(parents=True, exist_ok=True)
    annotations_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all JSON files in data/vlm_outputs/
    json_files = sorted(list(vlm_dir.glob("*.json")))
    if not json_files:
        print(f"No VLM annotation files found in {vlm_dir.relative_to(base_dir)}")
        print("Please place ChatGPT/VLM output JSON files in that folder and run this script again.")
        return
        
    print(f"Found {len(json_files)} VLM annotations to process.")
    success_count = 0
    for jf in json_files:
        try:
            process_vlm_annotation(jf, images_dir, annotations_dir)
            success_count += 1
        except Exception as e:
            print(f"  [Failed] Could not import {jf.name}: {e}")
            
    print(f"\nImport finished. Successfully imported {success_count}/{len(json_files)} annotations.")
    print("You can now refresh the web annotation tool to see and edit the imported annotations!")

if __name__ == "__main__":
    main()
