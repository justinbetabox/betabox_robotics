from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

STATE_DIR = Path.home() / ".local" / "state" / "betabox"


@dataclass(frozen=True)
class ManagedService:
    name: str
    title: str
    unit: str
    log_file: Path | None = None


MANAGED_SERVICES: dict[str, ManagedService] = {
    "hostname": ManagedService(
        name="hostname",
        title="Hostname",
        unit="set-hostname-from-serial.service",
    ),
    "boot-announce": ManagedService(
        name="boot-announce",
        title="Boot Announce",
        unit="betabox-boot-announce.service",
        log_file=STATE_DIR / "boot_announce.log",
    ),
    "monitor": ManagedService(
        name="monitor",
        title="Monitor",
        unit="betabox-monitor.service",
        log_file=STATE_DIR / "monitor.log",
    ),
    "jupyterhub": ManagedService(
        name="jupyterhub",
        title="JupyterHub",
        unit="jupyterhub.service",
    ),
    "video": ManagedService(
        name="video",
        title="Video",
        unit="car-video-api.service",
    ),
    "wifi-fallback": ManagedService(
        name="wifi-fallback",
        title="Wi-Fi Fallback",
        unit="wifi-fallback.service",
    ),
}
