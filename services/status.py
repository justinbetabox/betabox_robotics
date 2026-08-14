from __future__ import annotations

import argparse
import json
import shutil
import socket
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.hardware.ownership import (
    RobotOwnershipStatus,
    probe_robot_ownership,
)
from betabox_robotics.services.command import run
from betabox_robotics.services.guest import (
    GuestWorkspaceStatus,
    guest_status,
)
from betabox_robotics.services.guest import (
    print_status as print_guest_status,
)
from betabox_robotics.services.hardware_checks import (
    RobotHardwareStatus,
)
from betabox_robotics.services.hardware_status import (
    collect_hardware_status,
)
from betabox_robotics.services.managed import managed_services
from betabox_robotics.services.system_checks import (
    SystemHealthStatus,
)
from betabox_robotics.services.system_health import (
    collect_system_health,
)
from betabox_robotics.version import __version__

JSONValue = str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]


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


def _validate_flag(
    value: object,
    *,
    name: str,
) -> bool:
    if not isinstance(
        value,
        bool,
    ):
        raise TypeError(f"{name} must be a boolean")

    return value


@dataclass(frozen=True, slots=True)
class StatusReport:
    version: str
    hostname: str
    ip_addresses: tuple[str, ...]
    media_paths: dict[str, str]
    services: dict[str, str]
    jupyterhub_proxy_available: bool
    control: RobotOwnershipStatus
    hardware: RobotHardwareStatus
    system_health: SystemHealthStatus
    guest: GuestWorkspaceStatus

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

        object.__setattr__(
            self,
            "ip_addresses",
            tuple(
                _validate_string(
                    address,
                    name="ip address",
                )
                for address in self.ip_addresses
            ),
        )

        for name in (
            "media_paths",
            "services",
        ):
            value = cast(
                object,
                getattr(
                    self,
                    name,
                ),
            )

            if not isinstance(
                value,
                dict,
            ):
                raise TypeError(f"{name} must be a dictionary")

            mapping = cast(
                dict[object, object],
                value,
            )

            normalized = {
                _validate_string(
                    key,
                    name=f"{name} key",
                ): _validate_string(
                    item,
                    name=f"{name} value",
                )
                for key, item in mapping.items()
            }

            object.__setattr__(
                self,
                name,
                normalized,
            )

        _ = _validate_flag(
            self.jupyterhub_proxy_available,
            name="jupyterhub_proxy_available",
        )

    def to_dict(
        self,
    ) -> dict[str, JSONValue]:
        return cast(
            dict[str, JSONValue],
            asdict(self),
        )


def hostname() -> str:
    value = socket.gethostname()

    return _validate_string(
        value,
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
        value = address.strip()

        if not value:
            continue

        if (
            value.startswith("127.")
            or value == "0.0.0.0"
            or value == "::"
            or value == "::1"
        ):
            continue

        if value not in addresses:
            addresses.append(value)

    return tuple(addresses)


def service_status(
    service: str,
) -> str:
    service_value = _validate_string(
        service,
        name="service",
    )

    result = run(
        [
            "systemctl",
            "is-active",
            service_value,
        ],
        timeout=3,
    )

    if result is None:
        return "unknown"

    output = result.stdout.strip() or result.stderr.strip()

    return output or "unknown"


def executable_available(
    command: str,
) -> bool:
    command_value = _validate_string(
        command,
        name="command",
    )

    return shutil.which(command_value) is not None


def collect_status(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> StatusReport:
    config_value = _validate_config(config)
    managed = managed_services(config_value)

    services = {
        service.unit: service_status(service.unit) for service in managed.values()
    }

    return StatusReport(
        version=__version__,
        hostname=hostname(),
        ip_addresses=ip_addresses(),
        media_paths={
            "pictures": str(config_value.paths.pictures_dir),
            "videos": str(config_value.paths.videos_dir),
            "sounds": str(config_value.paths.sounds_dir),
        },
        services=services,
        jupyterhub_proxy_available=(executable_available("configurable-http-proxy")),
        control=probe_robot_ownership(),
        hardware=collect_hardware_status(config_value),
        system_health=collect_system_health(config_value),
        guest=guest_status(),
    )


def format_boolean(
    value: bool,
) -> str:
    value_value = _validate_flag(
        value,
        name="value",
    )

    return "available" if value_value else "missing"


def print_system_health(system_health: SystemHealthStatus) -> None:
    print()
    print("System Health")
    print("-------------")

    temperature = system_health.temperature

    if temperature.celsius is not None:
        print(f"CPU Temp:     {temperature.celsius:.1f} °C — {temperature.state}")
    else:
        print("CPU Temp:     unavailable")

    throttling = system_health.throttling

    print("Undervoltage: " + ("detected" if throttling.undervoltage_now else "no"))
    print("Throttling:   " + ("active" if throttling.throttled_now else "no"))

    memory = system_health.memory

    if memory.used_percent is not None:
        print(f"Memory:       {memory.used_percent:.1f}% — {memory.state}")
    else:
        print("Memory:       unavailable")

    disk = system_health.disk

    if disk.used_percent is not None:
        print(f"Disk:         {disk.used_percent:.1f}% — {disk.state}")
    else:
        print("Disk:         unavailable")

    print(
        "Ethernet:     "
        + ("connected" if system_health.ethernet.connected else "disconnected")
    )
    print(
        "Wi-Fi:        "
        + ("connected" if system_health.wifi.connected else "disconnected")
    )


def print_hardware_status(hardware: RobotHardwareStatus) -> None:
    print()
    print("Robot Hardware")
    print("--------------")

    print(
        "Passive Hardware:       "
        + f"{'available' if hardware.passive_hardware_available else 'unavailable'}"
    )

    print(f"I²C bus:     {format_boolean(hardware.i2c.available)}")

    if hardware.i2c.devices:
        print(f"I²C devices: {', '.join(hardware.i2c.devices)}")
    else:
        print("I²C devices: none detected")

    if hardware.battery.available and hardware.battery.voltage is not None:
        print(
            f"Battery:     {hardware.battery.voltage:.2f} V — {hardware.battery.state}"
        )
    else:
        print("Battery:     unavailable")

    if hardware.sensors.grayscale_available:
        values = hardware.sensors.grayscale_values or []
        formatted = ", ".join(str(value) for value in values)

        if hardware.sensors.grayscale_plausible is False:
            print(f"Grayscale: warning ({formatted})")
        else:
            print(f"Grayscale: available ({formatted})")

    else:
        print("Grayscale: unavailable")

    print(
        "Ultrasonic:  "
        + ("configured" if hardware.sensors.ultrasonic_configured else "not configured")
    )

    if hardware.audio.available:
        device = hardware.audio.device or "available"
        print(f"Audio:       {device}")
    else:
        print("Audio:       unavailable")

    if hardware.vision.service_available:
        if hardware.vision.camera_running and hardware.vision.camera_has_frame:
            vision_state = "healthy"
        elif hardware.vision.running:
            vision_state = "degraded"
        else:
            vision_state = "stopped"

        print(f"Vision:      {vision_state}")
        print(f"Clients:     {hardware.vision.clients}")
    else:
        print("Vision:      unavailable")


def print_human(
    report: StatusReport,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> None:
    config_value = _validate_config(config)
    print()
    print("Betabox Status")
    print("==============")
    print()

    print("Identity")
    print("--------")
    print(f"Version:  {report.version}")
    print(f"Hostname: {report.hostname}")

    if report.ip_addresses:
        print(f"IP:       {', '.join(report.ip_addresses)}")
    else:
        print("IP:       none found")

    print()
    print("Platform")
    print("--------")
    print("I2C:       " + ("available" if report.hardware.i2c.available else "missing"))

    print(
        "HifiBerry: " + ("available" if report.hardware.audio.available else "missing")
    )

    print_hardware_status(report.hardware)
    print_system_health(report.system_health)

    print()
    print("Media")
    print("-----")
    for name, path in report.media_paths.items():
        exists = path_available(path)
        print(f"{name.title():8} {path} {'OK' if exists else 'MISSING'}")

    print()

    print("Guest Workspace")
    print("----------------")

    print_guest_status(report.guest)

    print()

    print("Services")
    print("--------")
    managed = managed_services(config_value)
    for service in managed.values():
        state = report.services.get(
            service.unit,
            "unknown",
        )

        print(f"{service.title:16} {service.unit:34} {state}")

    print()
    print("JupyterHub")
    print("----------")
    print(
        f"Service:  {report.services.get(config_value.services.jupyterhub.unit, 'unknown')}"
    )
    print(
        f"Proxy:    {'available' if report.jupyterhub_proxy_available else 'missing'}"
    )
    print(f"Port:     {config_value.network.jupyterhub_port}")

    print()

    print("Launchpad")
    print("---------")
    print(
        f"Service:  {report.services.get(config_value.services.launchpad.unit, 'unknown')}"
    )
    print(f"Port:     {config_value.network.launchpad_port}")
    print(f"Endpoint: {config_value.network.launchpad_health_url}")

    print()


def path_available(
    path: str | Path,
) -> bool:
    if isinstance(path, str):
        path = path.strip()

        if not path:
            raise ValueError("path cannot be empty")

    path_value = Path(path).expanduser()

    try:
        return path_value.exists()
    except OSError:
        return False


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="betabox status")

    _ = parser.add_argument(
        "--json",
        action="store_true",
        help="Print status as JSON",
    )

    return parser.parse_args(argv)


def print_json(
    report: StatusReport,
) -> None:
    print(
        json.dumps(
            report.to_dict(),
            indent=2,
        )
    )


def main(
    argv: list[str] | None = None,
) -> int:
    config = DEFAULT_PLATFORM_CONFIG
    args = parse_args(argv)

    try:
        json_requested = _validate_flag(
            cast(
                object,
                args.json,
            ),
            name="json",
        )

        report = collect_status(config)

        if json_requested:
            print_json(report)
        else:
            print_human(
                report,
                config,
            )

    except (
        TypeError,
        ValueError,
        OSError,
    ) as exc:
        print(f"status failed: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
