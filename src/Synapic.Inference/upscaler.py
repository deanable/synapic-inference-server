"""Optional super-resolution hook.

The endpoint is explicit rather than returning an unchanged image when no
Swin2SR model is configured.
"""


class UpscaleUnavailable(RuntimeError):
    pass


def upscale(_image, _model_id: str | None = None):
    raise UpscaleUnavailable("no Swin2SR model is configured for this deployment")
