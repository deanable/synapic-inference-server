import io

from PIL import Image
from fastapi.testclient import TestClient

import service


client = TestClient(service.app)


def _image_bytes() -> bytes:
    image = Image.new("RGB", (2, 2), "red")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_health_is_available_without_model_weights():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_invalid_upload_is_rejected():
    response = client.post("/tag", files={"image": ("bad.txt", b"not an image", "text/plain")})
    assert response.status_code == 400


def test_tag_response_shape(monkeypatch):
    monkeypatch.setattr(service.model_loader, "caption", lambda *args: "A red bird on a branch")
    response = client.post("/tag", files={"image": ("photo.png", _image_bytes(), "image/png")})
    assert response.status_code == 200
    assert response.json()["tags"] == ["a", "red", "bird", "on", "branch"]


def test_upscale_reports_unconfigured_capability():
    response = client.post("/upscale", files={"image": ("photo.png", _image_bytes(), "image/png")})
    assert response.status_code == 501
