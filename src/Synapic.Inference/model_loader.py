"""Lazy Transformers model loading.

Keeping imports inside the loader makes ``/health`` and unit tests usable in a
minimal environment, while the production path still uses the pinned ML stack.
"""

from functools import lru_cache
from typing import Any


class ModelLoadError(RuntimeError):
    """Raised when configured model weights cannot be loaded."""


@lru_cache(maxsize=4)
def load_captioner(model_id: str, device: str) -> Any:
    try:
        from transformers import pipeline

        device_index = 0 if device.startswith("cuda") else -1
        return pipeline("image-to-text", model=model_id, device=device_index)
    except Exception as exc:  # give the API a stable, useful failure
        raise ModelLoadError(f"could not load image model {model_id!r}: {exc}") from exc


def caption(image: Any, model_id: str, device: str) -> str:
    result = load_captioner(model_id, device)(image, max_new_tokens=64)
    if not result or not isinstance(result, list) or "generated_text" not in result[0]:
        raise ModelLoadError("image model returned no caption")
    return str(result[0]["generated_text"]).strip()
