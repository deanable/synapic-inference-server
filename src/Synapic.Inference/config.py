"""Environment-backed configuration for the sidecar."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    model_id: str = "Salesforce/blip-image-captioning-base"
    device: str = "cpu"
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "info"
    max_image_bytes: int = 10 * 1024 * 1024
    queue_capacity: int = 16
    worker_count: int = 1

    def __post_init__(self) -> None:
        if self.queue_capacity < 1:
            raise ValueError("queue_capacity must be at least 1")
        if self.worker_count < 1:
            raise ValueError("worker_count must be at least 1")

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            model_id=os.getenv("SYNAPIC_MODEL_ID", cls.model_id),
            device=os.getenv("SYNAPIC_DEVICE", cls.device),
            host=os.getenv("SYNAPIC_HOST", cls.host),
            port=int(os.getenv("SYNAPIC_PORT", str(cls.port))),
            log_level=os.getenv("SYNAPIC_LOG_LEVEL", cls.log_level),
            max_image_bytes=int(os.getenv("SYNAPIC_MAX_IMAGE_BYTES", str(cls.max_image_bytes))),
            queue_capacity=int(os.getenv("SYNAPIC_QUEUE_CAPACITY", str(cls.queue_capacity))),
            worker_count=int(os.getenv("SYNAPIC_WORKER_COUNT", str(cls.worker_count))),
        )
