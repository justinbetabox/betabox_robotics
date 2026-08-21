from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)


def _validate_string(
    value: object,
    *,
    name: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")

    result = value.strip()

    if not result:
        raise ValueError(f"{name} cannot be empty")

    return result


def _validate_optional_path(
    value: object,
    *,
    name: str,
) -> Path | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(
        value,
        str | Path,
    ):
        raise TypeError(f"{name} must be a string, Path, or None")

    return Path(value).expanduser()


@dataclass(frozen=True, slots=True)
class ManagedService:
    name: str
    title: str
    unit: str
    log_file: Path | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "name",
            _validate_string(
                self.name,
                name="name",
            ),
        )
        object.__setattr__(
            self,
            "title",
            _validate_string(
                self.title,
                name="title",
            ),
        )
        object.__setattr__(
            self,
            "unit",
            _validate_string(
                self.unit,
                name="unit",
            ),
        )
        object.__setattr__(
            self,
            "log_file",
            _validate_optional_path(
                self.log_file,
                name="log_file",
            ),
        )


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
        "robot": ManagedService(
            name="robot",
            title=services.robot.display_name,
            unit=services.robot.unit,
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
        "guest-reset": ManagedService(
            name="guest-reset",
            title=services.guest_reset.display_name,
            unit=services.guest_reset.unit,
        ),
        "launchpad": ManagedService(
            name="launchpad",
            title=services.launchpad.display_name,
            unit=services.launchpad.unit,
        ),
    }


MANAGED_SERVICES: Mapping[str, ManagedService] = MappingProxyType(managed_services())
