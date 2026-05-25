import base64
import json
import random
import time
from io import BytesIO
from pathlib import Path
import requests
from PIL import Image

from semantic_guidance.experiment import inject_noise
from semantic_guidance.scoring import (
    coordinate_score,
    relation_score,
    scene_score,
    semantic_score_detailed,
    DEFAULT_WEIGHTS,
)

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGE_DIR = BASE_DIR / "data" / "images"
ANNOTATION_DIR = BASE_DIR / "data" / "annotations"
VLLM_API_URL = "http://localhost:8000/v1/chat/completions"
VLLM_MODEL = "/home/sz/Project/isr/models/Qwen3-VL-2B-Instruct"

def get_prefix(filename: str) -> str:
    """Extract prefix group (e.g., 'a' from 'a-01.json')."""
    base = Path(filename).stem
    if "-" in base:
        return base.split("-")[0]
    if "_" in base:
        return base.split("_")[0]
    return base

def query_local_qwen_vl_full_image(image_path: Path, candidate_bbox: list[int], expected_attributes: list[str], prompt_template: str | None = None, expected_relations: list[str] | None = None) -> tuple[bool, float, str, str]:
    """Query local Qwen-VL with the complete, uncropped full cloud-tilt image.
    Uses precise coordinate referencing [x, y, w, h] to focus VLM's attention on the candidate target inside the full context.
    Returns: (is_match, latency, reason, prompt_used)
    """
    start_time = time.time()
    if not image_path.exists():
        return False, 0.0, f"Image not found: {image_path.name}", ""
        
    try:
        # Load and convert full uncropped image to base64
        with Image.open(image_path) as img:
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
        relations_str = ", ".join(expected_relations) if expected_relations else "无位置约束"
        
        # Compute normalized coordinates for Qwen-VL [x_norm, y_norm, w_norm, h_norm] in [0, 1000] range
        img_w, img_h = img.size
        x_norm = max(0, min(int(round((candidate_bbox[0] / img_w) * 1000.0)), 1000))
        y_norm = max(0, min(int(round((candidate_bbox[1] / img_h) * 1000.0)), 1000))
        w_norm = max(1, min(int(round((candidate_bbox[2] / img_w) * 1000.0)), 1000 - x_norm))
        h_norm = max(1, min(int(round((candidate_bbox[3] / img_h) * 1000.0)), 1000 - y_norm))
        norm_bbox = [x_norm, y_norm, w_norm, h_norm]
        
        # Assemble standard prompt indicating exact target bounding box for reference
        if prompt_template:
            prompt = prompt_template.replace("{expected_attributes}", ", ".join(expected_attributes))
            prompt = prompt.replace("{attributes}", ", ".join(expected_attributes))
            prompt = prompt.replace("{expected_relations}", relations_str)
            prompt = prompt.replace("{relations}", relations_str)
            # Add implicit target reference to user-defined prompt
            prompt += (
                f"\n注：待研判目标在大图中的绝对像素包围框为：{candidate_bbox} (格式为 [左上角x, 左上角y, 宽度w, 高度h])，"
                f"对应的大图归一化坐标(0-1000范围)为：{norm_bbox} (格式为 [左上角x, 左上角y, 宽度w, 高度h])。"
            )
        else:
            rel_desc = f"，相对位置空间约束为：{relations_str}" if expected_relations else ""
            prompt = (
                "你是一个专业的图像物理解译与目标重识别专家。现在为你输入一幅由云台相机拍摄的完整宽视场大图。\n"
                f"在当前大图中，我们锁定的待研判候选目标边界框(Bounding Box)绝对像素坐标为：{candidate_bbox} (格式为 [左上角x, 左上角y, 宽度w, 高度h])，"
                f"对应的大图归一化坐标(0-1000范围，[x, y, w, h])为：{norm_bbox}。\n"
                f"前出侦察平台传回的语义目标包（STP）中，该真实目标的特征属性描述为：{', '.join(expected_attributes)}{rel_desc}。\n"
                "请结合完整图像中的空间地标与邻近拓扑背景，严格按照以下步骤进行分步研判论证：\n"
                "1. 在全图中根据归一化坐标[x, y, w, h]精确定位到指代的实体，详细研判其局部视觉特征（包括形状、颜色、材质、迷彩纹理、是否包含特征部件等），研判其是否符合STP中的属性特征；\n"
                "2. 结合全图中该目标周围呈现的其他背景、地标（如hangar机库、road道路等）或其它相邻实体，研判其空间拓扑关系是否完美契合STP中的位置约束描述；\n"
                "3. 综合上述两点，进行严密的逻辑比对，给出最终的匹配结论。\n\n"
                "【重要输出格式要求】\n"
                "请先输出您的详细步骤化解译论证过程，并在回答的最后，给出明确判定结论。如果是真实目标，请在最后一行单独输出“最终判定：是”；如果不是，请在最后一行单独输出“最终判定：否”。"
            )
        
        payload = {
            "model": VLLM_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 1024
        }
        
        # Query vLLM server
        headers = {"Content-Type": "application/json"}
        resp = requests.post(VLLM_API_URL, json=payload, headers=headers, timeout=20)
        latency = time.time() - start_time
        
        if resp.ok:
            content = resp.json()["choices"][0]["message"]["content"]
            # Flexible keyword matching for Chain-of-Thought Qwen reply
            last_lines = [line.strip() for line in content.split("\n") if line.strip()]
            is_match = False
            if last_lines:
                final_line = last_lines[-1]
                if "最终判定" in final_line:
                    is_match = "是" in final_line or "yes" in final_line.lower() or "符合" in final_line
                elif "最终判定" in content:
                    is_match = "最终判定：是" in content or "最终判定: 是" in content or "最终判定：符合" in content
                else:
                    is_match = "是" in final_line or "yes" in final_line.lower() or "符合" in final_line
            return is_match, latency, content, prompt
        else:
            return False, latency, f"vLLM API Error: HTTP {resp.status_code}", prompt
            
    except Exception as e:
        return False, time.time() - start_time, f"Execution error: {str(e)}", ""

def run_group_vlm_experiment(
    group_prefix: str,
    sigma: float,
    seed: int,
    use_real_vlm: bool = False,
    weights: dict | None = None,
    prompt_template: str | None = None
) -> dict:
    """Run A-Observer/B-Supporter experiment for a specific prefix group."""
    # Find files belonging to this group
    files = sorted([p for p in ANNOTATION_DIR.glob("*.json") if get_prefix(p.name) == group_prefix])
    if not files:
        return {"ok": False, "error": f"No files found for group: {group_prefix}"}
        
    # Observer (A-Platform) is the first file, e.g. a-01.json
    observer_path = files[0]
    supporter_paths = files[1:]
    
    with open(observer_path, "r", encoding="utf-8") as f:
        obs_data = json.load(f)
        
    target_id = obs_data.get("target_object_id", "")
    if not target_id:
        return {"ok": False, "error": f"Observer {observer_path.name} does not have target_object_id"}
        
    # Extract STP from Observer
    target_obj = next((o for o in obs_data["objects"] if o["id"] == target_id), None)
    if not target_obj:
        return {"ok": False, "error": f"Observer target {target_id} not found in objects"}
        
    expected_label = target_obj.get("label", "")
    expected_attributes = target_obj.get("attributes", [])
    expected_scene_tags = obs_data.get("scene_tags", [])
    
    # Extract expected spatial relations from observer perspective
    obj_label_map = {o["id"]: o.get("label", o["id"]) for o in obs_data["objects"]}
    expected_relations = []
    for r in obs_data.get("relations", []):
        sub = r.get("subject_id", "")
        obj = r.get("object_id", "")
        pred = r.get("predicate", "")
        if sub == target_id:
            ref_label = obj_label_map.get(obj, obj)
            expected_relations.append(f"位于 {ref_label} 的 {pred}")
        elif obj == target_id:
            ref_label = obj_label_map.get(sub, sub)
            expected_relations.append(f"{ref_label} 位于其 {pred}")
            
    # Batch statistics
    results = []
    logs = []
    
    logs.append(f"Observer loaded: {observer_path.name}")
    logs.append(f"  Target: {target_id} ({expected_label})")
    logs.append(f"  Attributes: {expected_attributes}")
    logs.append(f"  Relations: {expected_relations}")
    
    total_latency = 0.0
    vlm_calls = 0
    
    # Standardize weights setup aligned strictly with the paper
    w = dict(DEFAULT_WEIGHTS)
    if weights is None:
        config_path = Path("experiment_config.yaml")
        if config_path.exists():
            try:
                import yaml
                with config_path.open("r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    weights = config.get("scoring_weights", None)
            except Exception:
                pass
    if weights:
        w.update(weights)
    
    for supp_path in supporter_paths:
        with open(supp_path, "r", encoding="utf-8") as f:
            supp_data = json.load(f)
            
        supp_target_id = supp_data.get("target_object_id", "")
        if not supp_target_id:
            continue
            
        # Get actual target object in supporter
        supp_target = next((o for o in supp_data["objects"] if o["id"] == supp_target_id), None)
        if not supp_target:
            continue
            
        # 1. Inject noise onto supporter target center
        bbox_x, bbox_y, bbox_w, bbox_h = supp_target["bbox"]
        target_center = (bbox_x + bbox_w / 2.0, bbox_y + bbox_h / 2.0)
        noisy_point = inject_noise(target_center, sigma=sigma, seed=seed)
        
        # 2. Get candidates (target + distractors) in supporter
        # Locate annotated distractors and dynamically shift them close to target
        simulated_objects = []
        has_distractor = False
        for obj in supp_data["objects"]:
            if obj.get("type") == "distractor":
                has_distractor = True
                shifted_obj = {
                    **obj,
                    "bbox": [
                        supp_target["bbox"][0] + 120,
                        supp_target["bbox"][1] + 60,
                        obj["bbox"][2] if len(obj["bbox"]) > 2 else 50,
                        obj["bbox"][3] if len(obj["bbox"]) > 3 else 50,
                    ] if isinstance(obj["bbox"], list) else obj["bbox"]
                }
                simulated_objects.append(shifted_obj)
            else:
                simulated_objects.append(obj)
                
        # Generate decoy if not exist
        if not has_distractor:
            decoy = {
                "id": f"{supp_target_id}_decoy",
                "type": "distractor",
                "label": supp_target["label"],
                "bbox": [
                    supp_target["bbox"][0] + 120,
                    supp_target["bbox"][1] + 60,
                    supp_target["bbox"][2],
                    supp_target["bbox"][3]
                ],
                "attributes": ["decoy", "inactive"],
            }
            simulated_objects.append(decoy)
            
        candidates = [c for c in simulated_objects if c.get("type") in {"target", "distractor"}]
        
        # === Method A: Coordinate Method ===
        best_coord_candidate = max(candidates, key=lambda obj: coordinate_score(obj, noisy_point))
        coord_success = (best_coord_candidate["id"] == supp_target_id)
        
        # === Method B: Simulation Semantic Method ===
        best_sim_candidate = None
        best_sim_score = float("-inf")
        for c in candidates:
            score, _ = semantic_score_detailed(c, noisy_point, supp_data, weights=w)
            if score > best_sim_score:
                best_sim_score = score
                best_sim_candidate = c
        sim_success = (best_sim_candidate["id"] == supp_target_id) if best_sim_candidate else False
        
        # === Method C: Real Qwen-VL Method (Full Image Grounded Reasoning) ===
        best_vlm_candidate = None
        vlm_log_entry = {}
        
        if use_real_vlm:
            # Query Qwen-VL for each candidate using full cloud-tilt image
            img_filename = supp_data["image"].split("/")[-1]
            image_path = IMAGE_DIR / img_filename
            
            best_vlm_score = float("-inf")
            
            for c in candidates:
                # Call Qwen-VL on full uncropped image targeting c["bbox"]
                is_match, latency, reason, prompt_used = query_local_qwen_vl_full_image(
                    image_path, c["bbox"], expected_attributes, prompt_template=prompt_template, expected_relations=expected_relations
                )
                total_latency += latency
                vlm_calls += 1
                
                vlm_log_entry[c["id"]] = {
                    "is_match": is_match,
                    "latency": latency,
                    "reason": reason,
                    "prompt": prompt_used
                }
                
                # S1: Coordinate
                s_coord = coordinate_score(c, noisy_point)
                # S2: Relation
                s_rel = relation_score(c, supp_data, supp_target_id)
                # S3: Scene
                s_scene = scene_score(c, supp_data.get("scene_tags", []), expected_scene_tags)
                
                # S4 & S5: Category & Attribute Match (Physical VLM Evaluation)
                s_cat = 1.0 if (is_match and c.get("label") == expected_label) else 0.0
                s_attr = 1.0 if is_match else 0.0
                
                # Unified mathematical scoring strictly aligned with paper weights
                c_score = (
                    w["coordinate"] * s_coord +
                    w["category"] * s_cat +
                    w["attribute"] * s_attr +
                    w["relation"] * s_rel +
                    w["scene"] * s_scene
                )
                
                if c_score > best_vlm_score:
                    best_vlm_score = c_score
                    best_vlm_candidate = c
                    
            vlm_success = (best_vlm_candidate["id"] == supp_target_id) if best_vlm_candidate else False
        else:
            vlm_success = sim_success # fallback to simulated values
            
        # === Method D: YOLO Baseline (Traditional YOLOv8 + Coordinate Matching) ===
        img_filename = supp_data["image"].split("/")[-1]
        image_path = IMAGE_DIR / img_filename
        yolo_candidates = query_yolo_detector(image_path)
        
        yolo_success = False
        best_yolo_candidate = None
        
        if yolo_candidates:
            from math import dist
            def box_center_local(bbox):
                return (bbox[0] + bbox[2] / 2.0, bbox[1] + bbox[3] / 2.0)
            
            best_yolo_candidate = min(yolo_candidates, key=lambda obj: dist(box_center_local(obj["bbox"]), noisy_point))
            yolo_iou = compute_iou(best_yolo_candidate["bbox"], supp_target["bbox"])
            yolo_success = (yolo_iou > 0.5)
            
        results.append({
            "supporter": supp_path.stem,
            "noisy_point": [round(noisy_point[0], 1), round(noisy_point[1], 1)],
            "coordinate": {
                "selected": best_coord_candidate["id"],
                "success": coord_success
            },
            "simulation": {
                "selected": best_sim_candidate["id"] if best_sim_candidate else "",
                "success": sim_success
            },
            "vlm": {
                "selected": best_vlm_candidate["id"] if best_vlm_candidate else best_sim_candidate["id"],
                "success": vlm_success,
                "logs": vlm_log_entry if use_real_vlm else None
            },
            "yolo": {
                "selected": f"[{best_yolo_candidate['bbox'][0]},{best_yolo_candidate['bbox'][1]},{best_yolo_candidate['bbox'][2]},{best_yolo_candidate['bbox'][3]}]" if best_yolo_candidate else "未检测到",
                "success": yolo_success
            }
        })
        
        logs.append(f"Supporter evaluated: {supp_path.name}")
        logs.append(f"  Noisy Point: {results[-1]['noisy_point']}")
        logs.append(f"  Coordinate chose: {best_coord_candidate['id']} ({'Success' if coord_success else 'Fail'})")
        logs.append(f"  Semantic chose: {results[-1]['simulation']['selected']} ({'Success' if sim_success else 'Fail'})")
        logs.append(f"  YOLOv8 chose: {results[-1]['yolo']['selected']} ({'Success' if yolo_success else 'Fail'})")
        if use_real_vlm:
            logs.append(f"  Real Qwen3-VL chose: {results[-1]['vlm']['selected']} ({'Success' if vlm_success else 'Fail'})")
            
    avg_latency = total_latency / vlm_calls if vlm_calls > 0 else 0.0
    
    return {
        "ok": True,
        "group": group_prefix,
        "observer": observer_path.stem,
        "results": results,
        "avg_latency": avg_latency,
        "vlm_calls": vlm_calls,
        "logs": logs
    }


_yolo_model = None

def query_yolo_detector(image_path: Path) -> list[dict]:
    """Run YOLOv8 object detector on the image.
    Returns a list of detected objects: [{"bbox": [x, y, w, h], "label": "tank", "conf": float}]
    """
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            # Load lightweight YOLOv8 nano model
            _yolo_model = YOLO("yolov8n.pt")
        except ImportError:
            return []
            
    try:
        results = _yolo_model(str(image_path), verbose=False)
        detected = []
        if not results:
            return []
            
        result = results[0]
        # Class mapping: map boat (8), truck (7), car (2), bus (5), train (6) to 'tank'
        target_class_ids = {2, 5, 6, 7, 8}
        
        for box in result.boxes:
            class_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            if class_id in target_class_ids and conf >= 0.25:
                xyxy = box.xyxy[0].tolist()  # [xmin, ymin, xmax, ymax]
                xmin = int(round(xyxy[0]))
                ymin = int(round(xyxy[1]))
                xmax = int(round(xyxy[2]))
                ymax = int(round(xyxy[3]))
                w = max(1, xmax - xmin)
                h = max(1, ymax - ymin)
                
                detected.append({
                    "bbox": [xmin, ymin, w, h],
                    "label": "tank",
                    "conf": conf
                })
        return detected
    except Exception as e:
        print(f"YOLO detection error: {e}")
        return []

def compute_iou(boxA: list[int], boxB: list[int]) -> float:
    """Compute Intersection over Union (IoU) of two bounding boxes in [x, y, w, h] format."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
    yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])
    
    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = boxA[2] * boxA[3]
    boxBArea = boxB[2] * boxB[3]
    
    iou = interArea / float(boxAArea + boxBArea - interArea) if (boxAArea + boxBArea - interArea) > 0 else 0.0
    return iou
