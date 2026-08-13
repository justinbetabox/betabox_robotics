from __future__ import annotations

import shutil
import socket
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import cast

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.hardware.ownership import (
    RobotOwnershipStatus,
    probe_robot_ownership,
)
from betabox_robotics.robots.betabox_car import (
    BETABOX_CAR,
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

JSONValue = str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]


def _to_json_value(
    value: object,
) -> JSONValue:
    if value is None:
        return None

    if isinstance(
        value,
        str | int | float | bool,
    ):
        return value

    if isinstance(value, Mapping):
        mapping = cast(
            Mapping[object, object],
            value,
        )

        result: dict[str, JSONValue] = {}

        for key, item in mapping.items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings")

            result[key] = _to_json_value(item)

        return result

    if isinstance(
        value,
        list | tuple,
    ):
        values = cast(
            list[object] | tuple[object, ...],
            value,
        )

        return [_to_json_value(item) for item in values]

    raise TypeError(f"value is not JSON serializable: {type(value).__name__}")


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


@dataclass(
    frozen=True,
    slots=True,
)
class PlatformHardwareSummary:
    battery: BatteryStatus
    vision: VisionStatus

    def to_dict(
        self,
    ) -> dict[str, JSONValue]:
        battery = _to_json_value(self.battery.to_dict())
        vision = _to_json_value(self.vision.to_dict())

        if not isinstance(battery, dict):
            raise TypeError("battery data must be a JSON object")

        if not isinstance(vision, dict):
            raise TypeError("vision data must be a JSON object")

        return {
            "battery": battery,
            "vision": vision,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class PlatformSummary:
    version: str
    hostname: str
    ip_addresses: tuple[str, ...]
    services: Mapping[str, str]
    jupyterhub_proxy_available: bool
    control: RobotOwnershipStatus
    hardware: PlatformHardwareSummary
    system_health: SystemHealthStatus

    def __post_init__(
        self,
    ) -> None:
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

        normalized_addresses = tuple(
            _validate_string(
                address,
                name="ip address",
            )
            for address in self.ip_addresses
        )

        object.__setattr__(
            self,
            "ip_addresses",
            normalized_addresses,
        )

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

    def to_dict(
        self,
    ) -> dict[str, JSONValue]:
        control = _to_json_value(self.control.to_dict())
        system_health = _to_json_value(self.system_health.to_dict())

        if not isinstance(control, dict):
            raise TypeError("control data must be a JSON object")

        if not isinstance(system_health, dict):
            raise TypeError("system health data must be a JSON object")

        return {
            "version": self.version,
            "hostname": self.hostname,
            "ip_addresses": list(self.ip_addresses),
            "services": dict(self.services),
            "jupyterhub_proxy_available": (self.jupyterhub_proxy_available),
            "control": control,
            "hardware": self.hardware.to_dict(),
            "system_health": system_health,
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

    services: dict[str, str] = {
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
            battery=collect_battery_status(
                BETABOX_CAR.sensors,
            ),
            vision=collect_vision_status(
                config_value,
            ),
        ),
        system_health=collect_system_health(config_value),
    )
