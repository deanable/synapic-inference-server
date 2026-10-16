"""FastAPI entry point for the Synapic inference sidecar."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from io import BytesIO
import re
import time

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

import config
import model_loader
from upscaler import UpscaleUnavailable, upscale

settings = config.Settings.from_env()


class InferenceQueueSaturated(RuntimeError):
    """Raised when no slot is available in the inference queue."""


class InferenceQueueUnavailable(RuntimeError):
    """Raised when the inference queue is not accepting new work."""


@dataclass(slots=True)
class _InferenceJob:
    image: Image.Image
    result: asyncio.Future[str]


class InferenceQueue:
    """Run synchronous model calls away from the FastAPI event loop."""

    def __init__(self, capacity: int, worker_count: int, model_id: str, device: str) -> None:
        if capacity < 1:
            raise ValueError("inference queue capacity must be at least 1")
        if worker_count < 1:
            raise ValueError("inference worker count must be at least 1")

        self._queue: asyncio.Queue[_InferenceJob] = asyncio.Queue(maxsize=capacity)
        self._worker_count = worker_count
        self._model_id = model_id
        self._device = device
        self._workers: list[asyncio.Task[None]] = []
        self._accepting = False

    async def start(self) -> None:
        if self._workers:
            return

        self._accepting = True
        self._workers = [
            asyncio.create_task(self._worker(), name=f"synapic-inference-{index}")
            for index in range(self._worker_count)
        ]

    async def stop(self) -> None:
        self._accepting = False
        self._fail_queued_jobs()

        workers, self._workers = self._workers, []
        for worker in workers:
            worker.cancel()
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)

    async def submit(self, image: Image.Image) -> str:
        if not self._accepting:
            raise InferenceQueueUnavailable("inference queue is unavailable")

        result = asyncio.get_running_loop().create_future()
        try:
            self._queue.put_nowait(_InferenceJob(image=image, result=result))
        except asyncio.QueueFull as exc:
            result.cancel()
            raise InferenceQueueSaturated("inference queue is saturated") from exc

        try:
            return await result
        except asyncio.CancelledError:
            if not result.done():
                result.cancel()
            raise

    async def _worker(self) -> None:
        while True:
            job = await self._queue.get()
            try:
                try:
                    caption = await asyncio.to_thread(
                        model_loader.caption,
                        job.image,
                        self._model_id,
                        self._device,
                    )
                except asyncio.CancelledError:
                    self._fail_job(job)
                    raise
                except Exception as exc:
                    if not job.result.done():
                        job.result.set_exception(exc)
                else:
                    if not job.result.done():
                        job.result.set_result(caption)
            finally:
                self._queue.task_done()

    def _fail_queued_jobs(self) -> None:
        while True:
            try:
                job = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            self._fail_job(job)
            self._queue.task_done()

    @staticmethod
    def _fail_job(job: _InferenceJob) -> None:
        if not job.result.done():
            job.result.set_exception(InferenceQueueUnavailable("inference queue is unavailable"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    inference_queue = InferenceQueue(
        capacity=settings.queue_capacity,
        worker_count=settings.worker_count,
        model_id=settings.model_id,
        device=settings.device,
    )
    await inference_queue.start()
    app.state.inference_queue = inference_queue
    try:
        yield
    finally:
        await inference_queue.stop()
        app.state.inference_queue = None


app = FastAPI(title="Synapic inference", version="0.1.0", lifespan=lifespan)


def _tags(caption: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", caption.lower())
    return list(dict.fromkeys(words))[:32]


async def _read_image(upload: UploadFile) -> Image.Image:
    payload = await upload.read(settings.max_image_bytes + 1)
    if len(payload) > settings.max_image_bytes:
        raise HTTPException(status_code=413, detail="image exceeds configured size limit")
    try:
        image = Image.open(BytesIO(payload))
        image.load()
        return image.convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="uploaded file is not a valid image") from exc


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "model": settings.model_id, "device": settings.device}


@app.post("/tag")
async def tag(image: UploadFile = File(...)) -> JSONResponse:
    started = time.perf_counter()
    decoded = await _read_image(image)
    inference_queue = getattr(app.state, "inference_queue", None)
    if inference_queue is None:
        raise HTTPException(status_code=503, detail="inference queue is unavailable")
    try:
        caption = await inference_queue.submit(decoded)
    except InferenceQueueSaturated as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except InferenceQueueUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except model_loader.ModelLoadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return JSONResponse({
        "caption": caption,
        "tags": _tags(caption),
        "model": settings.model_id,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
    })


@app.post("/upscale")
async def upscale_image(image: UploadFile = File(...)):
    decoded = await _read_image(image)
    try:
        result = upscale(decoded)
    except UpscaleUnavailable as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port, log_level=settings.log_level)
