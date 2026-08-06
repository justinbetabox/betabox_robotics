from __future__ import annotations

import shutil
import socket
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.hardware.ownership import (
    RobotOwnershipStatus,
    probe_robot_ownership,
)
from betabox_robotics.services.command import run
from betabox_robotics.services.hardware_checks import (
    BatteryStatus,
    VisionStatus,
    collect_battery_status,
    collect_vision_status,
)
from betabox_robotics.services.managed import (
    managed_services,
)
from betabox_robotics.services.system_checks import (
    SystemHealthStatus,
)
from betabox_robotics.services.system_health import (
    collect_system_health,
)
from betabox_robotics.version import __version__


def _validate_config(
    value: object,
) -> PlatformConfig:
    if not isinstance(
        value,
        PlatformConfig,
    ):
        raise TypeError("config must be a PlatformConfig")

    return value


def _validate_string(
    value: object,
    *,
    name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(f"{name} must be a string")

    result = value.strip()

    if not result:
        raise ValueError(f"{name} cannot be empty")

    return result


@dataclass(frozen=True, slots=True)
class PlatformHardwareSummary:
    battery: BatteryStatus
    vision: VisionStatus

    def __post_init__(self) -> None:
        if not isinstance(
            self.battery,
            BatteryStatus,
        ):
            raise TypeError("battery must be a BatteryStatus")

        if not isinstance(
            self.vision,
            VisionStatus,
        ):
            raise TypeError("vision must be a VisionStatus")

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "battery": self.battery.to_dict(),
            "vision": self.vision.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class PlatformSummary:
    version: str
    hostname: str
    ip_addresses: tuple[str, ...]
    services: Mapping[str, str]
    jupyterhub_proxy_available: bool
    control: RobotOwnershipStatus
    hardware: PlatformHardwareSummary
    system_health: SystemHealthStatus

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "version",
            _validate_string(
                self.version,
                name="version",
            ),
        )
        object.__setattr__(
            self,
            "hostname",
            _validate_string(
                self.hostname,
                name="hostname",
            ),
        )

        if not isinstance(
            self.ip_addresses,
            tuple,
        ):
            raise TypeError("ip_addresses must be a tuple")

        for address in self.ip_addresses:
            _validate_string(
                address,
                name="IP address",
            )

        if not isinstance(
            self.services,
            Mapping,
        ):
            raise TypeError("services must be a mapping")

        normalized_services: dict[str, str] = {}

        for unit, state in self.services.items():
            unit_value = _validate_string(
                unit,
                name="service unit",
            )
            state_value = _validate_string(
                state,
                name="service state",
            )
            normalized_services[unit_value] = state_value

        object.__setattr__(
            self,
            "services",
            MappingProxyType(normalized_services),
        )

        if not isinstance(
            self.jupyterhub_proxy_available,
            bool,
        ):
            raise TypeError("jupyterhub_proxy_available must be a boolean")

        if not isinstance(
            self.control,
            RobotOwnershipStatus,
        ):
            raise TypeError("control must be a RobotOwnershipStatus")

        if not isinstance(
            self.hardware,
            PlatformHardwareSummary,
        ):
            raise TypeError("hardware must be a PlatformHardwareSummary")

        if not isinstance(
            self.system_health,
            SystemHealthStatus,
        ):
            raise TypeError("system_health must be a SystemHealthStatus")

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "version": self.version,
            "hostname": self.hostname,
            "ip_addresses": list(self.ip_addresses),
            "services": dict(self.services),
            "jupyterhub_proxy_available": (self.jupyterhub_proxy_available),
            "control": self.control.to_dict(),
            "hardware": self.hardware.to_dict(),
            "system_health": (self.system_health.to_dict()),
        }


def hostname() -> str:
    return _validate_string(
        socket.gethostname(),
        name="hostname",
    )


def ip_addresses() -> tuple[str, ...]:
    result = run(
        [
            "hostname",
            "-I",
        ],
        timeout=3,
    )

    if result is None or result.returncode != 0:
        return ()

    addresses: list[str] = []

    for address in result.stdout.split():
        address_value = address.strip()

        if not address_value or address_value.startswith("127."):
            continue

        if address_value not in addresses:
            addresses.append(address_value)

    return tuple(addresses)


def service_state(
    unit: str,
) -> str:
    unit_value = _validate_string(
        unit,
        name="unit",
    )

    result = run(
        [
            "systemctl",
            "is-active",
            unit_value,
        ],
        timeout=3,
    )

    if result is None:
        return "unknown"

    return result.stdout.strip() or result.stderr.strip() or "unknown"


def collect_platform_summary(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> PlatformSummary:
    config_value = _validate_config(config)
    managed = managed_services(config_value)

    services = {
        service.unit: service_state(service.unit) for service in managed.values()
    }

    return PlatformSummary(
        version=__version__,
        hostname=hostname(),
        ip_addresses=ip_addresses(),
        services=services,
        jupyterhub_proxy_available=(
            shutil.which("configurable-http-proxy") is not None
        ),
        control=probe_robot_ownership(),
        hardware=PlatformHardwareSummary(
            battery=collect_battery_status(config_value),
            vision=collect_vision_status(config_value),
        ),
        system_health=collect_system_health(config_value),
    )
