from __future__ import annotations

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.vision import (
    VisionClient,
    VisionClientError,
)

from .models import VisionStatus


def _validate_config(
    value: object,
) -> PlatformConfig:
    if not isinstance(
        value,
        PlatformConfig,
    ):
        raise TypeError("config must be a PlatformConfig")

    return value


def collect_vision_status(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> VisionStatus:
    """
    Collect the current Vision service and camera status.
    """

    config_value = _validate_config(config)

    client = VisionClient(
        base_url=(config_value.network.vision_url),
        timeout=float(config_value.verification.command_timeout_seconds),
    )

    try:
        statistics = client.statistics()
    except VisionClientError as exc:
        return VisionStatus(
            service_available=False,
            running=False,
            camera_running=False,
            camera_has_frame=False,
            clients=0,
            error=str(exc),
        )

    return VisionStatus(
        service_available=True,
        running=statistics.running,
        camera_running=(statistics.camera.running),
        camera_has_frame=(statistics.camera.has_frame),
        clients=(statistics.streaming.clients),
    )
