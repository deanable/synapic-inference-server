# Synapic inference server

An HTTP sidecar for image caption/tag inference. The service keeps model loading
lazy and explicit so the health endpoint and the test suite work without model
weights or network access.

## Requirements

* Python 3.11.9 (the version is pinned in `.python-version`)
* A CPU or CUDA-capable machine for model inference

## Setup

```sh
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

The first request to `/tag` downloads `SYNAPIC_MODEL_ID` from Hugging Face
unless the model is already in the local cache. For an offline deployment,
pre-populate that cache during image construction or mount it at runtime.

## Run

```sh
make run
# or: uvicorn service:app --app-dir src/Synapic.Inference --host 0.0.0.0 --port 8080
```

Check readiness with `GET /health`. Submit an image with:

```sh
curl -F image=@photo.jpg http://localhost:8080/tag
```

`POST /tag` returns a caption and a stable list of lower-case tags extracted
from that caption. `POST /upscale` is intentionally reported as unavailable
until a compatible Swin2SR model is configured; this avoids silently returning
the original image as a false upscale result.

## Test and build

```sh
make test
make build
```

The test command does not load model weights and can run without network access
after dependencies have been installed. Build the
container reproducibly with:

```sh
docker build -t synapic-inference:local .
docker run --rm -p 8080:8080 --env-file .env synapic-inference:local
```

## Configuration

See `.env.example`. `SYNAPIC_DEVICE=cpu` is the portable default. Set
`SYNAPIC_MODEL_ID` to a locally cached image-to-text Transformers model when
running without network access.
