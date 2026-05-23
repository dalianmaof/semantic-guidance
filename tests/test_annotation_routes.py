from app import create_app


def test_index_route_returns_html():
    app = create_app()
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.content_type
