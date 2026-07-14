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
    return {
        "hostname": ManagedService(
            name="hostname",
            title="Hostname",
            unit="set-hostname-from-serial.service",
        ),
        "boot-announce": ManagedService(
            name="boot-announce",
            title="Boot Announce",
            unit="betabox-boot-announce.service",
            log_file=config.paths.boot_announce_log,
        ),
        "monitor": ManagedService(
            name="monitor",
            title="Monitor",
            unit="betabox-monitor.service",
            log_file=config.paths.monitor_log,
        ),
        "jupyterhub": ManagedService(
            name="jupyterhub",
            title="JupyterHub",
            unit="jupyterhub.service",
        ),
        "video": ManagedService(
            name="video",
            title="Video",
            unit="betabox-video.service",
            log_file=config.paths.video_log,
        ),
        "wifi-fallback": ManagedService(
            name="wifi-fallback",
            title="Wi-Fi Fallback",
            unit="wifi-fallback.service",
        ),
    }


MANAGED_SERVICES = managed_services()
