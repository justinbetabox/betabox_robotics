from __future__ import annotations

import json
import shutil
import socket
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from betabox_robotics.services.hardware_status import (
    RobotHardwareStatus,
    collect_hardware_status,
)
from betabox_robotics.services.system_health import (
    SystemHealthStatus,
    collect_system_health,
)
from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)

from betabox_robotics.hardware.ownership import (
    RobotOwnershipStatus,
    probe_robot_ownership,
)

from betabox_robotics.services.managed import managed_services
from betabox_robotics.version import __version__


@dataclass(frozen=True)
class StatusReport:
    version: str
    hostname: str
    ip_addresses: list[str]
    media_paths: dict[str, str]
    services: dict[str, str]
    jupyterhub_proxy_available: bool
    control: RobotOwnershipStatus
    hardware: RobotHardwareStatus
    system_health: SystemHealthStatus

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run(command: list[str], timeout: int = 5) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception:
        return None


def hostname() -> str:
    return socket.gethostname()


def ip_addresses() -> list[str]:
    result = run(["hostname", "-I"], timeout=3)

    if result is None or result.returncode != 0:
        return []

    addresses: list[str] = []

    for address in result.stdout.split():
        address = address.strip()

        if not address:
            continue

        if address.startswith("127."):
            continue

        if address not in addresses:
            addresses.append(address)

    return addresses


def service_status(service: str) -> str:
    result = run(["systemctl", "is-active", service], timeout=3)

    if result is None:
        return "unknown"

    return result.stdout.strip() or "unknown"


def executable_available(
    command: str,
) -> bool:
    return (
        shutil.which(command)
        is not None
    )


def collect_status(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> StatusReport:
    managed = managed_services(config)

    services = {
        service.unit: service_status(service.unit)
        for service in managed.values()
    }

    hardware = collect_hardware_status(config)
    system_health = collect_system_health(config)

    return StatusReport(
        version=__version__,
        hostname=hostname(),
        ip_addresses=ip_addresses(),
        media_paths={
            "pictures": str(config.paths.pictures_dir),
            "videos": str(config.paths.videos_dir),
            "sounds": str(config.paths.sounds_dir),
        },
        services=services,
        jupyterhub_proxy_available=executable_available("configurable-http-proxy"),
        control=probe_robot_ownership(),
        hardware=hardware,
        system_health=system_health,
    )


def format_boolean(value: bool) -> str:
    return "available" if value else "missing"


def print_system_health(system_health: SystemHealthStatus) -> None:
    print()
    print("System Health")
    print("-------------")

    temperature = system_health.temperature

    if temperature.celsius is not None:
        print(
            f"CPU Temp:     {temperature.celsius:.1f} °C "
            f"— {temperature.state}"
        )
    else:
        print("CPU Temp:     unavailable")

    throttling = system_health.throttling

    print(
        "Undervoltage: "
        + ("detected" if throttling.undervoltage_now else "no")
    )
    print(
        "Throttling:   "
        + ("active" if throttling.throttled_now else "no")
    )

    memory = system_health.memory

    if memory.used_percent is not None:
        print(
            f"Memory:       {memory.used_percent:.1f}% "
            f"— {memory.state}"
        )
    else:
        print("Memory:       unavailable")

    disk = system_health.disk

    if disk.used_percent is not None:
        print(
            f"Disk:         {disk.used_percent:.1f}% "
            f"— {disk.state}"
        )
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
        f"Passive Hardware:       "
        f"{'available' if hardware.passive_hardware_available else 'unavailable'}"
    )

    print(f"I²C bus:     {format_boolean(hardware.i2c.available)}")

    if hardware.i2c.devices:
        print(f"I²C devices: {', '.join(hardware.i2c.devices)}")
    else:
        print("I²C devices: none detected")

    if hardware.battery.available and hardware.battery.voltage is not None:
        print(
            f"Battery:     {hardware.battery.voltage:.2f} V "
            f"— {hardware.battery.state}"
        )
    else:
        print("Battery:     unavailable")

    if hardware.sensors.grayscale_available:
        values = hardware.sensors.grayscale_values or []
        formatted = ", ".join(str(value) for value in values)
        print(f"Grayscale:   available ({formatted})")
    else:
        print("Grayscale:   unavailable")

    print(
        "Ultrasonic:  "
        + (
            "configured"
            if hardware.sensors.ultrasonic_configured
            else "not configured"
        )
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
    print(
        "I2C:       "
        + (
            "available"
            if report.hardware.i2c.available
            else "missing"
        )
    )

    print(
        "HifiBerry: "
        + (
            "available"
            if report.hardware.audio.available
            else "missing"
        )
    )

    print_hardware_status(report.hardware)
    print_system_health(report.system_health)

    print()
    print("Media")
    print("-----")
    for name, path in report.media_paths.items():
        exists = Path(path).exists()
        print(f"{name.title():8} {path} {'OK' if exists else 'MISSING'}")

    print()
    print("Services")
    print("--------")
    managed = managed_services(config)
    for service in managed.values():
        state = report.services.get(
            service.unit,
            "unknown",
        )

        print(
            f"{service.title:16} "
            f"{service.unit:34} "
            f"{state}"
        )

    print()
    print("JupyterHub")
    print("----------")
    print(
        f"Service:  "
        f"{report.services.get(config.services.jupyterhub.unit, 'unknown')}"
    )
    print(
        f"Proxy:    "
        f"{'available' if report.jupyterhub_proxy_available else 'missing'}"
    )
    print(f"Port:     {config.network.jupyterhub_port}")

    print()

    print("Launchpad")
    print("---------")
    print(
        "Service:  "
        f"{report.services.get(config.services.launchpad.unit, 'unknown')}"
    )
    print(f"Port:     {config.network.launchpad_port}")
    print(
        f"Endpoint: {config.network.launchpad_health_url}"
    )

    print()


def main(
    argv: list[str] | None = None,
) -> int:
    config = DEFAULT_PLATFORM_CONFIG
    report = collect_status(config)

    if argv and "--json" in argv:
        print(
            json.dumps(
                report.to_dict(),
                indent=2,
            )
        )
    else:
        print_human(
            report,
            config,
        )

    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
