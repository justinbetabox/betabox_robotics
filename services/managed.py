from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)


@dataclass(frozen=True)
class ManagedService:
    name: str
    title: str
    unit: str
    log_file: Path | None = None


def managed_services(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> dict[str, ManagedService]:
    services = config.services

    return {
        "hostname": ManagedService(
            name="hostname",
            title=services.hostname.display_name,
            unit=services.hostname.unit,
        ),
        "boot-announce": ManagedService(
            name="boot-announce",
            title=services.boot_announce.display_name,
            unit=services.boot_announce.unit,
            log_file=config.paths.boot_announce_log,
        ),
        "monitor": ManagedService(
            name="monitor",
            title=services.monitor.display_name,
            unit=services.monitor.unit,
            log_file=config.paths.monitor_log,
        ),
        "jupyterhub": ManagedService(
            name="jupyterhub",
            title=services.jupyterhub.display_name,
            unit=services.jupyterhub.unit,
        ),
        "video": ManagedService(
            name="video",
            title=services.video.display_name,
            unit=services.video.unit,
            log_file=config.paths.video_log,
        ),
        "wifi-fallback": ManagedService(
            name="wifi-fallback",
            title=services.wifi_fallback.display_name,
            unit=services.wifi_fallback.unit,
        ),
        "launchpad": ManagedService(
            name="launchpad",
            title=services.launchpad.display_name,
            unit=services.launchpad.unit,
        ),
    }


MANAGED_SERVICES = managed_services()
