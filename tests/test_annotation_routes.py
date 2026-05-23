from app import create_app


def test_index_route_returns_html():
    app = create_app()
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.content_type


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


def test_index_html_contains_annotation_shell():
    app = create_app()
    client = app.test_client()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert "image-list" in html
    assert "annotation-canvas" in html
    assert "save-button" in html


def test_index_html_starts_with_disabled_action_buttons():
    app = create_app()
    client = app.test_client()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert 'id="save-button" disabled' in html
    assert 'id="add-object-button" type="button" disabled' in html
