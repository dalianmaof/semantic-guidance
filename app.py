import json
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory, Response

from semantic_guidance.annotation_store import AnnotationStore
from semantic_guidance.online_experiment import run_group_vlm_experiment


def create_app() -> Flask:
    app = Flask(__name__)

    base_dir = Path(__file__).resolve().parent
    image_dir_env = os.getenv("SEMANTIC_GUIDANCE_IMAGE_DIR")
    if image_dir_env:
        image_dir = Path(image_dir_env).resolve()
    else:
        image_dir = (base_dir / "data" / "images").resolve()

    annotation_dir_env = os.getenv("SEMANTIC_GUIDANCE_ANNOTATION_DIR")
    if annotation_dir_env:
        annotation_dir = Path(annotation_dir_env).resolve()
    else:
        annotation_dir = (base_dir / "data" / "annotations").resolve()

    store = AnnotationStore(image_dir=image_dir, annotation_dir=annotation_dir)

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.get("/api/images")
    def list_images():
        return jsonify({"images": store.list_images()})

    @app.get("/api/annotations/<image_name>")
    def load_annotation(image_name: str):
        return jsonify(store.load_annotation(image_name))

    @app.post("/api/annotations/<image_name>")
    def save_annotation(image_name: str):
        payload = request.get_json(force=True)
        try:
            store.save_annotation(image_name, payload)
        except ValueError as e:
            return jsonify({"ok": False, "error": str(e)}), 400
        return jsonify({"ok": True})

    @app.get("/data/images/<path:image_name>")
    def get_image(image_name: str):
        return send_from_directory(image_dir, image_name)

    @app.get("/experiment")
    def experiment_view() -> str:
        return render_template("experiment.html")

    @app.get("/api/experiment/stream")
    def stream_experiment():
        # Parse query params
        groups_str = request.args.get("groups", "a")
        groups = [g.strip().lower() for g in groups_str.split(",") if g.strip()]
        
        sigma = float(request.args.get("sigma", 30.0))
        
        seeds_str = request.args.get("seeds", "1")
        seeds = [int(s.strip()) for s in seeds_str.split(",") if s.strip()]
        
        use_real_vlm = request.args.get("use_real_vlm", "false").lower() == "true"
        prompt_template = request.args.get("prompt_template", "").strip()
        if not prompt_template:
            prompt_template = None

        def event_generator():
            total_steps = len(groups) * len(seeds)
            completed_steps = 0
            all_results = []
            
            mode_str = 'VLM在线大模型' if use_real_vlm else '数学模型仿真模拟'
            group_names = [g.upper() for g in groups]
            start_payload = {
                'type': 'start',
                'message': f'启动批量重识别对照实验。评测组: {group_names}，种子数: {len(seeds)}，定位噪差(Sigma): {sigma}px，模式: {mode_str}'
            }
            yield f"data: {json.dumps(start_payload)}\n\n"
            
            for seed in seeds:
                for group in groups:
                    grp_upper = group.upper()
                    prog = int((completed_steps / total_steps) * 100)
                    prog_payload = {
                        'type': 'progress_update',
                        'message': f'正在评估 场景{grp_upper} 组 (种子: {seed})...',
                        'progress': prog
                    }
                    yield f"data: {json.dumps(prog_payload)}\n\n"
                    
                    try:
                        res = run_group_vlm_experiment(
                            group_prefix=group,
                            sigma=sigma,
                            seed=seed,
                            use_real_vlm=use_real_vlm,
                            prompt_template=prompt_template
                        )
                        
                        if res.get("ok"):
                            all_results.append(res)
                            for log_line in res.get("logs", []):
                                log_payload = {'type': 'log', 'message': log_line}
                                yield f"data: {json.dumps(log_payload)}\n\n"
                        else:
                            err_msg = res.get('error', '未知错误')
                            err_payload = {
                                'type': 'error',
                                'message': f'组 {grp_upper} 运行错误: {err_msg}'
                            }
                            yield f"data: {json.dumps(err_payload)}\n\n"
                    except Exception as e:
                        ex_msg = str(e)
                        ex_payload = {
                            'type': 'error',
                            'message': f'评估组 {grp_upper} (种子 {seed}) 异常: {ex_msg}'
                        }
                        yield f"data: {json.dumps(ex_payload)}\n\n"
                        
                    completed_steps += 1
            
            # Calculate aggregate statistics
            total_supporters = 0
            coord_successes = 0
            sim_successes = 0
            vlm_successes = 0
            yolo_successes = 0
            total_vlm_latency = 0.0
            total_vlm_calls = 0
            
            for res in all_results:
                total_supporters += len(res["results"])
                total_vlm_latency += res["avg_latency"] * res["vlm_calls"]
                total_vlm_calls += res["vlm_calls"]
                for r in res["results"]:
                    if r["coordinate"]["success"]:
                        coord_successes += 1
                    if r["simulation"]["success"]:
                        sim_successes += 1
                    if r["vlm"]["success"]:
                        vlm_successes += 1
                    if r.get("yolo", {}).get("success"):
                        yolo_successes += 1
                        
            avg_latency = total_vlm_latency / total_vlm_calls if total_vlm_calls > 0 else 0.0
            
            coord_rate = (coord_successes / total_supporters * 100.0) if total_supporters > 0 else 0.0
            sim_rate = (sim_successes / total_supporters * 100.0) if total_supporters > 0 else 0.0
            vlm_rate = (vlm_successes / total_supporters * 100.0) if total_supporters > 0 else 0.0
            yolo_rate = (yolo_successes / total_supporters * 100.0) if total_supporters > 0 else 0.0
            
            summary = {
                "total_supporters": total_supporters,
                "coord_rate": round(coord_rate, 2),
                "sim_rate": round(sim_rate, 2),
                "vlm_rate": round(vlm_rate, 2),
                "yolo_rate": round(yolo_rate, 2),
                "avg_latency": round(avg_latency, 3),
                "total_vlm_calls": total_vlm_calls,
                "all_results": all_results
            }
            
            done_payload = {
                'type': 'done',
                'message': '批量对照实验全部执行完毕！',
                'summary': summary
            }
            yield f"data: {json.dumps(done_payload)}\n\n"
            
        return Response(event_generator(), mimetype="text/event-stream")

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
