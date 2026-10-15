"""FastAPI entry point for the Synapic inference sidecar."""

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
app = FastAPI(title="Synapic inference", version="0.1.0")


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
    try:
        caption = model_loader.caption(decoded, settings.model_id, settings.device)
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
