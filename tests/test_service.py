import asyncio
import io
import threading
import time

import pytest
from PIL import Image
from fastapi.testclient import TestClient

import service


@pytest.fixture
def client():
    with TestClient(service.app) as test_client:
        yield test_client


def _image_bytes() -> bytes:
    image = Image.new("RGB", (2, 2), "red")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_health_is_available_without_model_weights(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_invalid_upload_is_rejected(client):
    response = client.post("/tag", files={"image": ("bad.txt", b"not an image", "text/plain")})
    assert response.status_code == 400


def test_tag_response_shape(client, monkeypatch):
    monkeypatch.setattr(service.model_loader, "caption", lambda *args: "A red bird on a branch")
    response = client.post("/tag", files={"image": ("photo.png", _image_bytes(), "image/png")})
    assert response.status_code == 200
    assert response.json()["tags"] == ["a", "red", "bird", "on", "branch"]


def test_upscale_reports_unconfigured_capability(client):
    response = client.post("/upscale", files={"image": ("photo.png", _image_bytes(), "image/png")})
    assert response.status_code == 501


def test_inference_queue_is_bounded_and_does_not_block_event_loop(monkeypatch):
    started = threading.Event()
    release = threading.Event()

    def blocking_caption(*args):
        started.set()
        while not release.is_set():
            time.sleep(0.001)
        return "A queued caption"

    monkeypatch.setattr(service.model_loader, "caption", blocking_caption)

    async def exercise_queue():
        queue = service.InferenceQueue(
            capacity=1,
            worker_count=1,
            model_id="test-model",
            device="cpu",
        )
        await queue.start()
        try:
            first = asyncio.create_task(queue.submit(object()))
            assert await asyncio.to_thread(started.wait, 1)

            second = asyncio.create_task(queue.submit(object()))
            await asyncio.sleep(0)

            with pytest.raises(service.InferenceQueueSaturated):
                await queue.submit(object())

            await asyncio.wait_for(asyncio.sleep(0.01), timeout=0.2)
            release.set()
            assert await asyncio.wait_for(first, timeout=1) == "A queued caption"
            assert await asyncio.wait_for(second, timeout=1) == "A queued caption"
        finally:
            release.set()
            await queue.stop()

    asyncio.run(exercise_queue())


def test_tag_returns_429_when_inference_queue_is_saturated(client):
    class SaturatedQueue:
        async def submit(self, image):
            raise service.InferenceQueueSaturated("inference queue is saturated")

    service.app.state.inference_queue = SaturatedQueue()
    response = client.post("/tag", files={"image": ("photo.png", _image_bytes(), "image/png")})
    assert response.status_code == 429


def test_tag_returns_503_when_inference_queue_is_unavailable(client):
    class UnavailableQueue:
        async def submit(self, image):
            raise service.InferenceQueueUnavailable("inference queue is unavailable")

    service.app.state.inference_queue = UnavailableQueue()
    response = client.post("/tag", files={"image": ("photo.png", _image_bytes(), "image/png")})
    assert response.status_code == 503
