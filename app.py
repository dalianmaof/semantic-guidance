import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

from semantic_guidance.annotation_store import AnnotationStore


def create_app() -> Flask:
    app = Flask(__name__)
    image_dir = Path(os.getenv("SEMANTIC_GUIDANCE_IMAGE_DIR", "data/images"))
    annotation_dir = Path(os.getenv("SEMANTIC_GUIDANCE_ANNOTATION_DIR", "data/annotations"))
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
        store.save_annotation(image_name, payload)
        return jsonify({"ok": True})

    @app.get("/data/images/<path:image_name>")
    def get_image(image_name: str):
        return send_from_directory(image_dir, image_name)

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
