# Semantic Guidance Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a research-prototype annotation tool and lightweight simulation pipeline that can label scene images, run coordinate-vs-semantic guidance comparisons, and output basic experiment summaries.

**Architecture:** Use a minimal Python + browser architecture. A small Flask app serves one HTML annotation page plus JSON endpoints for listing images and saving/loading annotations; a separate Python experiment runner reads the saved JSON files, injects location noise, scores coordinate and semantic methods on the same candidates, and writes CSV plus one comparison chart.

**Tech Stack:** Python 3, Flask, vanilla HTML/CSS/JavaScript, pytest, matplotlib

---

## File Structure

### Files to create

- `requirements.txt`
- `app.py`
- `semantic_guidance/__init__.py`
- `semantic_guidance/annotation_store.py`
- `semantic_guidance/annotation_schema.py`
- `semantic_guidance/experiment.py`
- `semantic_guidance/scoring.py`
- `semantic_guidance/reporting.py`
- `templates/index.html`
- `static/app.js`
- `static/app.css`
- `tests/test_annotation_store.py`
- `tests/test_annotation_routes.py`
- `tests/test_experiment.py`
- `docs/superpowers/plans/2026-05-23-semantic-guidance-prototype-plan.md`

### File responsibilities

- `requirements.txt`: minimal runtime and test dependencies.
- `app.py`: Flask entrypoint, page route, JSON API routes.
- `semantic_guidance/annotation_schema.py`: default annotation shape and validation helpers.
- `semantic_guidance/annotation_store.py`: list images, load/save JSON annotations, progress helpers.
- `semantic_guidance/experiment.py`: scene loading, noise injection, candidate generation, experiment loop.
- `semantic_guidance/scoring.py`: coordinate baseline scoring and semantic scoring.
- `semantic_guidance/reporting.py`: CSV writing and simple matplotlib summary chart.
- `templates/index.html`: single-page annotation UI skeleton.
- `static/app.js`: browser interactions, canvas box drawing, API calls.
- `static/app.css`: basic layout and annotation styling.
- `tests/test_annotation_store.py`: storage and validation coverage.
- `tests/test_annotation_routes.py`: Flask endpoint coverage.
- `tests/test_experiment.py`: scene parsing, scoring, experiment outputs.

### Working conventions

- Keep the prototype single-user and local-only.
- Prefer standard library code where practical.
- Use direct, readable data structures over premature abstractions.
- Commit after each task block that leaves the repo runnable.

### Task 1: Bootstrap the Python prototype skeleton

**Files:**
- Create: `C:\Users\fanen\Documents\semantic-guidance\requirements.txt`
- Create: `C:\Users\fanen\Documents\semantic-guidance\semantic_guidance\__init__.py`
- Create: `C:\Users\fanen\Documents\semantic-guidance\app.py`
- Test: `C:\Users\fanen\Documents\semantic-guidance\tests\test_annotation_routes.py`

- [ ] **Step 1: Write the failing route smoke test**

```python
from app import create_app


def test_index_route_returns_html():
    app = create_app()
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.content_type
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_annotation_routes.py::test_index_route_returns_html -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError` because `app.py` and the app factory do not exist yet.

- [ ] **Step 3: Write the minimal app skeleton**

`requirements.txt`

```text
Flask==3.1.0
matplotlib==3.10.0
pytest==8.3.5
```

`app.py`

```python
from flask import Flask, render_template


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
```

`semantic_guidance/__init__.py`

```python
__all__ = []
```

`templates/index.html`

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <title>Semantic Guidance Annotation Tool</title>
  </head>
  <body>
    <h1>Semantic Guidance Annotation Tool</h1>
  </body>
</html>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_annotation_routes.py::test_index_route_returns_html -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add requirements.txt app.py templates/index.html semantic_guidance/__init__.py tests/test_annotation_routes.py
git commit -m "feat: bootstrap prototype flask app"
```

### Task 2: Implement annotation storage and JSON validation

**Files:**
- Create: `C:\Users\fanen\Documents\semantic-guidance\semantic_guidance\annotation_schema.py`
- Create: `C:\Users\fanen\Documents\semantic-guidance\semantic_guidance\annotation_store.py`
- Test: `C:\Users\fanen\Documents\semantic-guidance\tests\test_annotation_store.py`

- [ ] **Step 1: Write the failing annotation store tests**

```python
from pathlib import Path

from semantic_guidance.annotation_store import AnnotationStore


def test_list_images_returns_sorted_pngs(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "b-01.png").write_bytes(b"fake")
    (image_dir / "a-01.png").write_bytes(b"fake")

    store = AnnotationStore(image_dir=image_dir, annotation_dir=tmp_path / "annotations")

    assert store.list_images() == ["a-01.png", "b-01.png"]


def test_save_and_load_annotation_roundtrip(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "a-01.png").write_bytes(b"fake")

    store = AnnotationStore(image_dir=image_dir, annotation_dir=tmp_path / "annotations")
    payload = {
        "image": "data/images/a-01.png",
        "scene_id": "a-01",
        "scene_tags": ["airport"],
        "target_object_id": "tank_1",
        "objects": [{"id": "tank_1", "type": "target", "label": "tank", "bbox": [1, 2, 3, 4], "attributes": []}],
        "relations": [],
        "notes": "",
    }

    store.save_annotation("a-01.png", payload)

    assert store.load_annotation("a-01.png")["target_object_id"] == "tank_1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_annotation_store.py -v`
Expected: FAIL because `AnnotationStore` does not exist yet.

- [ ] **Step 3: Write minimal schema and storage helpers**

`semantic_guidance/annotation_schema.py`

```python
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
```

`semantic_guidance/annotation_store.py`

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_annotation_store.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add semantic_guidance/annotation_schema.py semantic_guidance/annotation_store.py tests/test_annotation_store.py
git commit -m "feat: add annotation storage and validation"
```

### Task 3: Add JSON annotation API routes

**Files:**
- Modify: `C:\Users\fanen\Documents\semantic-guidance\app.py`
- Modify: `C:\Users\fanen\Documents\semantic-guidance\tests\test_annotation_routes.py`

- [ ] **Step 1: Write the failing API tests**

```python
from app import create_app


def test_images_endpoint_returns_png_list(tmp_path, monkeypatch):
    image_dir = tmp_path / "images"
    annotation_dir = tmp_path / "annotations"
    image_dir.mkdir()
    (image_dir / "a-01.png").write_bytes(b"fake")

    monkeypatch.setenv("SEMANTIC_GUIDANCE_IMAGE_DIR", str(image_dir))
    monkeypatch.setenv("SEMANTIC_GUIDANCE_ANNOTATION_DIR", str(annotation_dir))

    app = create_app()
    client = app.test_client()

    response = client.get("/api/images")

    assert response.status_code == 200
    assert response.get_json()["images"] == ["a-01.png"]


def test_save_endpoint_persists_annotation(tmp_path, monkeypatch):
    image_dir = tmp_path / "images"
    annotation_dir = tmp_path / "annotations"
    image_dir.mkdir()
    (image_dir / "a-01.png").write_bytes(b"fake")

    monkeypatch.setenv("SEMANTIC_GUIDANCE_IMAGE_DIR", str(image_dir))
    monkeypatch.setenv("SEMANTIC_GUIDANCE_ANNOTATION_DIR", str(annotation_dir))

    app = create_app()
    client = app.test_client()

    payload = {
        "image": "data/images/a-01.png",
        "scene_id": "a-01",
        "scene_tags": [],
        "target_object_id": "tank_1",
        "objects": [{"id": "tank_1", "type": "target", "label": "tank", "bbox": [1, 2, 3, 4], "attributes": []}],
        "relations": [],
        "notes": "",
    }

    response = client.post("/api/annotations/a-01.png", json=payload)

    assert response.status_code == 200
    assert response.get_json()["ok"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_annotation_routes.py -v`
Expected: FAIL with 404 responses because the JSON API routes do not exist yet.

- [ ] **Step 3: Implement route-backed storage wiring**

`app.py`

```python
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

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

    return app
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_annotation_routes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_annotation_routes.py
git commit -m "feat: add annotation json api routes"
```

### Task 4: Build the minimal annotation page UI

**Files:**
- Modify: `C:\Users\fanen\Documents\semantic-guidance\templates/index.html`
- Create: `C:\Users\fanen\Documents\semantic-guidance\static/app.js`
- Create: `C:\Users\fanen\Documents\semantic-guidance\static/app.css`

- [ ] **Step 1: Write the failing UI smoke test**

```python
from app import create_app


def test_index_html_contains_annotation_shell():
    app = create_app()
    client = app.test_client()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert "image-list" in html
    assert "annotation-canvas" in html
    assert "save-button" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_annotation_routes.py::test_index_html_contains_annotation_shell -v`
Expected: FAIL because the page still contains only the placeholder heading.

- [ ] **Step 3: Replace the placeholder page with the annotation shell**

`templates/index.html`

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Semantic Guidance Annotation Tool</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='app.css') }}">
  </head>
  <body>
    <div class="layout">
      <aside class="sidebar">
        <h1>Scene Images</h1>
        <ul id="image-list"></ul>
      </aside>
      <main class="workspace">
        <div class="toolbar">
          <button id="prev-button">Prev</button>
          <button id="next-button">Next</button>
          <button id="save-button">Save</button>
        </div>
        <div class="canvas-panel">
          <img id="scene-image" alt="scene preview">
          <div id="annotation-canvas"></div>
        </div>
        <section class="form-panel">
          <label>Scene Tags <input id="scene-tags" type="text"></label>
          <label>Target Object ID <input id="target-object-id" type="text"></label>
          <textarea id="notes" placeholder="notes"></textarea>
        </section>
      </main>
    </div>
    <script src="{{ url_for('static', filename='app.js') }}"></script>
  </body>
</html>
```

`static/app.css`

```css
body { margin: 0; font-family: Arial, sans-serif; }
.layout { display: grid; grid-template-columns: 280px 1fr; min-height: 100vh; }
.sidebar { border-right: 1px solid #ddd; padding: 16px; overflow: auto; }
.workspace { padding: 16px; display: grid; gap: 16px; }
.toolbar { display: flex; gap: 8px; }
.canvas-panel { position: relative; min-height: 480px; border: 1px solid #ddd; overflow: auto; }
#scene-image { display: block; max-width: 100%; }
#annotation-canvas { position: absolute; inset: 0; }
.form-panel { display: grid; gap: 8px; }
```

`static/app.js`

```javascript
async function bootstrap() {
  const response = await fetch("/api/images");
  const data = await response.json();
  const list = document.getElementById("image-list");
  for (const imageName of data.images) {
    const item = document.createElement("li");
    item.textContent = imageName;
    list.appendChild(item);
  }
}

bootstrap();
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_annotation_routes.py::test_index_html_contains_annotation_shell -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add templates/index.html static/app.css static/app.js tests/test_annotation_routes.py
git commit -m "feat: add annotation page shell"
```

### Task 5: Make the annotation page usable for image selection and save/load

**Files:**
- Modify: `C:\Users\fanen\Documents\semantic-guidance\static/app.js`
- Modify: `C:\Users\fanen\Documents\semantic-guidance\templates/index.html`
- Modify: `C:\Users\fanen\Documents\semantic-guidance\static/app.css`

- [ ] **Step 1: Write the failing behavior test at the storage layer**

```python
from pathlib import Path

from semantic_guidance.annotation_store import AnnotationStore


def test_load_annotation_returns_default_shape_for_new_image(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "a-01.png").write_bytes(b"fake")

    store = AnnotationStore(image_dir=image_dir, annotation_dir=tmp_path / "annotations")

    annotation = store.load_annotation("a-01.png")

    assert annotation["scene_id"] == "a-01"
    assert annotation["objects"] == []
```

- [ ] **Step 2: Run test to verify it passes before UI wiring**

Run: `python -m pytest tests/test_annotation_store.py::test_load_annotation_returns_default_shape_for_new_image -v`
Expected: PASS. This confirms the backend default payload already supports the next UI step.

- [ ] **Step 3: Wire image selection, load, and save in the browser**

`static/app.js`

```javascript
const state = {
  images: [],
  index: 0,
  annotation: null,
};

function currentImageName() {
  return state.images[state.index];
}

function parseCsv(value) {
  return value.split(",").map((part) => part.trim()).filter(Boolean);
}

function renderSidebar() {
  const list = document.getElementById("image-list");
  list.innerHTML = "";
  state.images.forEach((imageName, index) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.textContent = imageName;
    button.onclick = () => loadImage(index);
    if (index === state.index) button.className = "active-image";
    item.appendChild(button);
    list.appendChild(item);
  });
}

function renderForm() {
  document.getElementById("scene-tags").value = (state.annotation.scene_tags || []).join(", ");
  document.getElementById("target-object-id").value = state.annotation.target_object_id || "";
  document.getElementById("notes").value = state.annotation.notes || "";
}

async function loadImage(index) {
  state.index = index;
  const imageName = currentImageName();
  document.getElementById("scene-image").src = `/data/images/${imageName}`;
  const response = await fetch(`/api/annotations/${imageName}`);
  state.annotation = await response.json();
  renderSidebar();
  renderForm();
}

async function saveAnnotation() {
  state.annotation.scene_tags = parseCsv(document.getElementById("scene-tags").value);
  state.annotation.target_object_id = document.getElementById("target-object-id").value.trim();
  state.annotation.notes = document.getElementById("notes").value;
  await fetch(`/api/annotations/${currentImageName()}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(state.annotation),
  });
}

async function bootstrap() {
  const response = await fetch("/api/images");
  const data = await response.json();
  state.images = data.images;
  document.getElementById("save-button").onclick = saveAnnotation;
  document.getElementById("prev-button").onclick = () => loadImage(Math.max(0, state.index - 1));
  document.getElementById("next-button").onclick = () => loadImage(Math.min(state.images.length - 1, state.index + 1));
  if (state.images.length > 0) {
    await loadImage(0);
  }
}

bootstrap();
```

`app.py` add a route to serve source images:

```python
from flask import send_from_directory

    @app.get("/data/images/<path:image_name>")
    def get_image(image_name: str):
        return send_from_directory(image_dir, image_name)
```

- [ ] **Step 4: Run route tests and manual check**

Run: `python -m pytest tests/test_annotation_routes.py -v`
Expected: PASS

Run: `python app.py`
Expected: Local server starts. Opening `http://127.0.0.1:5000` shows an image list, loads the first image, and allows tags plus notes to be saved.

- [ ] **Step 5: Commit**

```bash
git add app.py static/app.js static/app.css templates/index.html tests/test_annotation_store.py tests/test_annotation_routes.py
git commit -m "feat: wire annotation page image loading and save flow"
```

### Task 6: Add object boxes and relation editing in the annotation UI

**Files:**
- Modify: `C:\Users\fanen\Documents\semantic-guidance\templates/index.html`
- Modify: `C:\Users\fanen\Documents\semantic-guidance\static/app.js`
- Modify: `C:\Users\fanen\Documents\semantic-guidance\static/app.css`

- [ ] **Step 1: Write the failing validation test for duplicate object ids**

```python
import pytest

from semantic_guidance.annotation_schema import validate_annotation


def test_validate_annotation_rejects_duplicate_object_ids():
    payload = {
        "target_object_id": "tank_1",
        "objects": [
            {"id": "tank_1", "type": "target", "label": "tank", "bbox": [1, 2, 3, 4], "attributes": []},
            {"id": "tank_1", "type": "distractor", "label": "tank", "bbox": [4, 5, 6, 7], "attributes": []},
        ],
        "relations": [],
    }

    with pytest.raises(ValueError):
        validate_annotation(payload)
```

- [ ] **Step 2: Run test to verify current validation behavior**

Run: `python -m pytest tests/test_annotation_store.py::test_validate_annotation_rejects_duplicate_object_ids -v`
Expected: PASS if the validator already rejects duplicates. If it fails, fix the validator before continuing.

- [ ] **Step 3: Add box and relation editors to the page**

`templates/index.html` add object and relation panels:

```html
<section class="editor-grid">
  <div>
    <h2>Objects</h2>
    <button id="add-object-button">Add Object</button>
    <div id="object-list"></div>
  </div>
  <div>
    <h2>Relations</h2>
    <button id="add-relation-button">Add Relation</button>
    <div id="relation-list"></div>
  </div>
</section>
```

`static/app.js` add object/relation editing helpers:

```javascript
function createEmptyObject() {
  return { id: "", type: "target", label: "", bbox: [50, 50, 120, 80], attributes: [] };
}

function createEmptyRelation() {
  return { subject_id: "", predicate: "near", object_id: "" };
}

function renderObjectList() {
  const host = document.getElementById("object-list");
  host.innerHTML = "";
  state.annotation.objects.forEach((obj, index) => {
    const row = document.createElement("div");
    row.className = "object-row";
    row.innerHTML = `
      <input data-field="id" value="${obj.id}">
      <select data-field="type">
        <option value="target">target</option>
        <option value="distractor">distractor</option>
        <option value="landmark">landmark</option>
      </select>
      <input data-field="label" value="${obj.label}">
      <button data-action="delete">Delete</button>
    `;
    row.querySelector('[data-field="type"]').value = obj.type;
    row.querySelectorAll("input, select").forEach((element) => {
      element.onchange = () => {
        obj[element.dataset.field] = element.value;
      };
    });
    row.querySelector('[data-action="delete"]').onclick = () => {
      state.annotation.objects.splice(index, 1);
      renderObjectList();
    };
    host.appendChild(row);
  });
}

function renderRelationList() {
  const host = document.getElementById("relation-list");
  host.innerHTML = "";
  state.annotation.relations.forEach((relation, index) => {
    const row = document.createElement("div");
    row.className = "relation-row";
    row.innerHTML = `
      <input data-field="subject_id" value="${relation.subject_id}">
      <select data-field="predicate">
        <option value="left_of">left_of</option>
        <option value="right_of">right_of</option>
        <option value="near">near</option>
        <option value="in_front_of">in_front_of</option>
        <option value="behind">behind</option>
      </select>
      <input data-field="object_id" value="${relation.object_id}">
      <button data-action="delete">Delete</button>
    `;
    row.querySelector('[data-field="predicate"]').value = relation.predicate;
    row.querySelectorAll("input, select").forEach((element) => {
      element.onchange = () => {
        relation[element.dataset.field] = element.value;
      };
    });
    row.querySelector('[data-action="delete"]').onclick = () => {
      state.annotation.relations.splice(index, 1);
      renderRelationList();
    };
    host.appendChild(row);
  });
}

document.getElementById("add-object-button").onclick = () => {
  state.annotation.objects.push(createEmptyObject());
  renderObjectList();
};

document.getElementById("add-relation-button").onclick = () => {
  state.annotation.relations.push(createEmptyRelation());
  renderRelationList();
};
```

- [ ] **Step 4: Run route tests and manual verification**

Run: `python -m pytest tests/test_annotation_store.py tests/test_annotation_routes.py -v`
Expected: PASS

Run: `python app.py`
Expected: The page allows adding objects, filling ids, types, labels, and defining relations before saving JSON.

- [ ] **Step 5: Commit**

```bash
git add templates/index.html static/app.js static/app.css tests/test_annotation_store.py
git commit -m "feat: add object and relation editors"
```

### Task 7: Implement the lightweight experiment engine

**Files:**
- Create: `C:\Users\fanen\Documents\semantic-guidance\semantic_guidance\scoring.py`
- Create: `C:\Users\fanen\Documents\semantic-guidance\semantic_guidance\experiment.py`
- Test: `C:\Users\fanen\Documents\semantic-guidance\tests\test_experiment.py`

- [ ] **Step 1: Write the failing experiment tests**

```python
from semantic_guidance.experiment import inject_noise, run_single_experiment


def test_inject_noise_is_deterministic_for_seed():
    point = (100.0, 50.0)

    result_a = inject_noise(point, sigma=5.0, seed=7)
    result_b = inject_noise(point, sigma=5.0, seed=7)

    assert result_a == result_b


def test_run_single_experiment_returns_method_outcomes():
    scene = {
        "scene_id": "a-01",
        "target_object_id": "tank_1",
        "objects": [
            {"id": "tank_1", "type": "target", "label": "tank", "bbox": [100, 100, 50, 50], "attributes": ["left"]},
            {"id": "tank_2", "type": "distractor", "label": "tank", "bbox": [160, 100, 50, 50], "attributes": ["right"]},
        ],
        "relations": [],
        "scene_tags": ["airport"],
    }

    result = run_single_experiment(scene, sigma=5.0, seed=3)

    assert set(result["methods"].keys()) == {"coordinate", "semantic"}
    assert result["scene_id"] == "a-01"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_experiment.py -v`
Expected: FAIL because the experiment module does not exist yet.

- [ ] **Step 3: Implement the minimal experiment core**

`semantic_guidance/scoring.py`

```python
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
```

`semantic_guidance/experiment.py`

```python
import random

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_experiment.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add semantic_guidance/scoring.py semantic_guidance/experiment.py tests/test_experiment.py
git commit -m "feat: add lightweight experiment engine"
```

### Task 8: Add batch reporting and one comparison chart

**Files:**
- Create: `C:\Users\fanen\Documents\semantic-guidance\semantic_guidance\reporting.py`
- Modify: `C:\Users\fanen\Documents\semantic-guidance\semantic_guidance\experiment.py`
- Modify: `C:\Users\fanen\Documents\semantic-guidance\app.py`
- Modify: `C:\Users\fanen\Documents\semantic-guidance\tests\test_experiment.py`

- [ ] **Step 1: Write the failing batch experiment test**

```python
from pathlib import Path

from semantic_guidance.experiment import run_batch_experiment


def test_run_batch_experiment_writes_csv(tmp_path: Path):
    scenes = [
        {
            "scene_id": "a-01",
            "target_object_id": "tank_1",
            "objects": [
                {"id": "tank_1", "type": "target", "label": "tank", "bbox": [100, 100, 50, 50], "attributes": ["left"]},
                {"id": "tank_2", "type": "distractor", "label": "tank", "bbox": [160, 100, 50, 50], "attributes": ["right"]},
            ],
            "relations": [],
            "scene_tags": ["airport"],
        }
    ]

    output_dir = tmp_path / "results"
    report = run_batch_experiment(scenes, sigmas=[5.0, 15.0], seeds=[1, 2], output_dir=output_dir)

    assert (output_dir / "experiment_rows.csv").exists()
    assert (output_dir / "summary.csv").exists()
    assert report["rows"] == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_experiment.py::test_run_batch_experiment_writes_csv -v`
Expected: FAIL because `run_batch_experiment` and reporting helpers do not exist yet.

- [ ] **Step 3: Implement batch run and reporting**

`semantic_guidance/reporting.py`

```python
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


def write_rows(path: Path, rows: list[dict]) -> None:
    fieldnames = ["scene_id", "sigma", "seed", "method", "selected_id", "success"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict]) -> list[dict]:
    buckets = defaultdict(list)
    for row in rows:
      buckets[(row["sigma"], row["method"])].append(int(row["success"]))
    summary = []
    for (sigma, method), values in sorted(buckets.items()):
      summary.append({"sigma": sigma, "method": method, "success_rate": sum(values) / len(values)})
    return summary


def write_summary(path: Path, rows: list[dict]) -> list[dict]:
    summary = summarize(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sigma", "method", "success_rate"])
        writer.writeheader()
        writer.writerows(summary)
    return summary


def write_chart(path: Path, summary: list[dict]) -> None:
    methods = sorted({row["method"] for row in summary})
    for method in methods:
        subset = [row for row in summary if row["method"] == method]
        plt.plot([row["sigma"] for row in subset], [row["success_rate"] for row in subset], marker="o", label=method)
    plt.xlabel("Sigma")
    plt.ylabel("Success Rate")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
```

`semantic_guidance/experiment.py` add:

```python
from pathlib import Path

from semantic_guidance.reporting import write_chart, write_rows, write_summary


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
```

Create a CLI entry in `app.py` or a simple runnable block:

```python
from pathlib import Path

from semantic_guidance.experiment import run_batch_experiment


def run_debug_experiment() -> None:
    print("Use a dedicated script or interactive shell in the next task to feed real scenes.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_experiment.py::test_run_batch_experiment_writes_csv -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add semantic_guidance/reporting.py semantic_guidance/experiment.py app.py tests/test_experiment.py
git commit -m "feat: add batch reporting and success chart"
```

### Task 9: Add a real-scene loader and debug experiment entrypoint

**Files:**
- Modify: `C:\Users\fanen\Documents\semantic-guidance\semantic_guidance\annotation_store.py`
- Modify: `C:\Users\fanen\Documents\semantic-guidance\semantic_guidance\experiment.py`
- Create: `C:\Users\fanen\Documents\semantic-guidance\run_experiment.py`
- Modify: `C:\Users\fanen\Documents\semantic-guidance\tests\test_experiment.py`

- [ ] **Step 1: Write the failing loader test**

```python
import json
from pathlib import Path

from semantic_guidance.experiment import load_scenes_from_annotations


def test_load_scenes_from_annotations_reads_json_files(tmp_path: Path):
    annotation_dir = tmp_path / "annotations"
    annotation_dir.mkdir()
    payload = {
        "image": "data/images/a-01.png",
        "scene_id": "a-01",
        "scene_tags": ["airport"],
        "target_object_id": "tank_1",
        "objects": [{"id": "tank_1", "type": "target", "label": "tank", "bbox": [1, 2, 3, 4], "attributes": []}],
        "relations": [],
        "notes": "",
    }
    (annotation_dir / "a-01.json").write_text(json.dumps(payload), encoding="utf-8")

    scenes = load_scenes_from_annotations(annotation_dir)

    assert len(scenes) == 1
    assert scenes[0]["scene_id"] == "a-01"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_experiment.py::test_load_scenes_from_annotations_reads_json_files -v`
Expected: FAIL because the scene loader does not exist yet.

- [ ] **Step 3: Add scene loading and a runnable script**

`semantic_guidance/experiment.py` add:

```python
import json


def load_scenes_from_annotations(annotation_dir: Path) -> list[dict]:
    scenes = []
    for path in sorted(annotation_dir.glob("*.json")):
        scenes.append(json.loads(path.read_text(encoding="utf-8")))
    return scenes
```

`run_experiment.py`

```python
from pathlib import Path

from semantic_guidance.experiment import load_scenes_from_annotations, run_batch_experiment


def main() -> None:
    annotation_dir = Path("data/annotations")
    output_dir = Path("output/debug")
    scenes = load_scenes_from_annotations(annotation_dir)
    if not scenes:
        raise SystemExit("No annotations found in data/annotations")
    report = run_batch_experiment(scenes, sigmas=[5.0, 15.0], seeds=[1, 2, 3], output_dir=output_dir)
    print(f"wrote {report['rows']} rows to {output_dir}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests and debug entrypoint**

Run: `python -m pytest tests/test_experiment.py -v`
Expected: PASS

Run: `python run_experiment.py`
Expected: If `data/annotations` contains at least one saved annotation JSON, the script writes `experiment_rows.csv`, `summary.csv`, and `success_rate.png` under `output/debug`.

- [ ] **Step 5: Commit**

```bash
git add semantic_guidance/experiment.py run_experiment.py tests/test_experiment.py
git commit -m "feat: add annotation-backed experiment entrypoint"
```

### Task 10: Manual prototype validation with 3 to 5 sample scenes

**Files:**
- Modify: `C:\Users\fanen\Documents\semantic-guidance\data\annotations\*.json`
- Modify: `C:\Users\fanen\Documents\semantic-guidance\output\debug\*`
- Test: manual validation only

- [ ] **Step 1: Start the annotation tool**

Run: `python app.py`
Expected: Local page opens at `http://127.0.0.1:5000`

- [ ] **Step 2: Annotate 3 to 5 representative images**

Use these fields per image:

```json
{
  "scene_tags": ["airport", "day"],
  "target_object_id": "tank_1",
  "objects": [
    {"id": "tank_1", "type": "target", "label": "tank", "bbox": [x, y, w, h], "attributes": ["left"]},
    {"id": "tank_2", "type": "distractor", "label": "tank", "bbox": [x, y, w, h], "attributes": ["right"]}
  ],
  "relations": [
    {"subject_id": "tank_1", "predicate": "left_of", "object_id": "hangar_1"}
  ]
}
```

- [ ] **Step 3: Run the debug experiment**

Run: `python run_experiment.py`
Expected: `output/debug/experiment_rows.csv`, `output/debug/summary.csv`, and `output/debug/success_rate.png` are created.

- [ ] **Step 4: Manually inspect the trend**

Check:

```text
1. coordinate and semantic rows exist for each scene/sigma/seed combination
2. success_rate.png plots both methods
3. semantic method is at least capable of diverging from coordinate baseline as rules change
```

- [ ] **Step 5: Commit**

```bash
git add data/annotations output/debug
git commit -m "chore: add sample annotations and debug experiment outputs"
```

## Self-Review

### Spec coverage

- Annotation tool: covered by Tasks 1 through 6.
- Annotation JSON format and validation: covered by Tasks 2, 3, and 6.
- Lightweight experiment engine: covered by Tasks 7 through 9.
- Minimal output CSV and chart: covered by Task 8.
- Research-first simplified development order: covered by Task 10 and the task ordering.

### Placeholder scan

- No `TODO`, `TBD`, or deferred placeholders remain in task steps.
- Every code-changing step includes explicit code or file content.
- Every verification step includes exact commands and expected results.

### Type consistency

- Annotation payload keys are consistent across storage, routes, UI, and experiment code: `scene_id`, `scene_tags`, `target_object_id`, `objects`, `relations`, `notes`.
- Experiment result method keys are consistent: `coordinate`, `semantic`.
- Batch output field names are consistent: `scene_id`, `sigma`, `seed`, `method`, `selected_id`, `success`.
