from __future__ import annotations

import shutil
import socket
import subprocess
from dataclasses import asdict, dataclass
from typing import Any

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.hardware.ownership import (
    RobotOwnershipStatus,
    probe_robot_ownership,
)
from betabox_robotics.services.hardware_status import (
    BatteryStatus,
    VisionStatus,
    collect_battery_status,
    collect_vision_status,
)
from betabox_robotics.services.managed import (
    managed_services,
)
from betabox_robotics.services.system_health import (
    SystemHealthStatus,
    collect_system_health,
)
from betabox_robotics.version import __version__


@dataclass(frozen=True)
class PlatformHardwareSummary:
    battery: BatteryStatus
    vision: VisionStatus


@dataclass(frozen=True)
class PlatformSummary:
    version: str
    hostname: str
    ip_addresses: list[str]
    services: dict[str, str]
    jupyterhub_proxy_available: bool
    control: RobotOwnershipStatus
    hardware: PlatformHardwareSummary
    system_health: SystemHealthStatus

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run(
    command: list[str],
    *,
    timeout: int = 3,
) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception:
        return None


def hostname() -> str:
    return socket.gethostname()


def ip_addresses() -> list[str]:
    result = run(
        [
            "hostname",
            "-I",
        ],
        timeout=3,
    )

    if (
        result is None
        or result.returncode != 0
    ):
        return []

    addresses: list[str] = []

    for address in result.stdout.split():
        address = address.strip()

        if (
            not address
            or address.startswith("127.")
        ):
            continue

        if address not in addresses:
            addresses.append(address)

    return addresses


def service_state(
    unit: str,
) -> str:
    result = run(
        [
            "systemctl",
            "is-active",
            unit,
        ],
        timeout=3,
    )

    if result is None:
        return "unknown"

    return (
        result.stdout.strip()
        or "unknown"
    )


def collect_platform_summary(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> PlatformSummary:
    managed = managed_services(
        config
    )

    services = {
        service.unit: service_state(
            service.unit
        )
        for service in managed.values()
    }

    return PlatformSummary(
        version=__version__,
        hostname=hostname(),
        ip_addresses=ip_addresses(),
        services=services,
        jupyterhub_proxy_available=(
            shutil.which(
                "configurable-http-proxy"
            )
            is not None
        ),
        control=probe_robot_ownership(),
        hardware=PlatformHardwareSummary(
            battery=collect_battery_status(
                config
            ),
            vision=collect_vision_status(
                config
            ),
        ),
        system_health=collect_system_health(
            config
        ),
    )
