from __future__ import annotations

import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TemperatureStatus:
    celsius: float | None
    state: str
    error: str | None = None


@dataclass(frozen=True)
class ThrottlingStatus:
    raw: str | None
    undervoltage_now: bool
    undervoltage_occurred: bool
    throttled_now: bool
    throttled_occurred: bool
    error: str | None = None


@dataclass(frozen=True)
class MemoryStatus:
    total_mb: int | None
    available_mb: int | None
    used_percent: float | None
    state: str
    error: str | None = None


@dataclass(frozen=True)
class DiskStatus:
    path: str
    total_gb: float | None
    free_gb: float | None
    used_percent: float | None
    state: str
    error: str | None = None


@dataclass(frozen=True)
class NetworkInterfaceStatus:
    name: str
    available: bool
    connected: bool
    state: str
    connection: str | None
    error: str | None = None


@dataclass(frozen=True)
class SystemHealthStatus:
    temperature: TemperatureStatus
    throttling: ThrottlingStatus
    memory: MemoryStatus
    disk: DiskStatus
    ethernet: NetworkInterfaceStatus
    wifi: NetworkInterfaceStatus

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

def collect_temperature_status() -> TemperatureStatus:
    path = Path("/sys/class/thermal/thermal_zone0/temp")

    try:
        raw = path.read_text(encoding="utf-8").strip()
        celsius = float(raw) / 1000.0
    except Exception as exc:
        return TemperatureStatus(
            celsius=None,
            state="unknown",
            error=str(exc),
        )

    if celsius >= 85.0:
        state = "critical"
    elif celsius >= 75.0:
        state = "high"
    else:
        state = "normal"

    return TemperatureStatus(
        celsius=celsius,
        state=state,
    )

def collect_throttling_status() -> ThrottlingStatus:
    result = run(["vcgencmd", "get_throttled"], timeout=5)

    if result is None or result.returncode != 0:
        return ThrottlingStatus(
            raw=None,
            undervoltage_now=False,
            undervoltage_occurred=False,
            throttled_now=False,
            throttled_occurred=False,
            error="vcgencmd get_throttled failed",
        )

    output = result.stdout.strip()

    try:
        value = int(output.split("=", maxsplit=1)[1], 16)
    except Exception as exc:
        return ThrottlingStatus(
            raw=output,
            undervoltage_now=False,
            undervoltage_occurred=False,
            throttled_now=False,
            throttled_occurred=False,
            error=str(exc),
        )

    return ThrottlingStatus(
        raw=f"0x{value:x}",
        undervoltage_now=bool(value & (1 << 0)),
        throttled_now=bool(value & (1 << 2)),
        undervoltage_occurred=bool(value & (1 << 16)),
        throttled_occurred=bool(value & (1 << 18)),
    )

def collect_memory_status() -> MemoryStatus:
    try:
        values: dict[str, int] = {}

        with Path("/proc/meminfo").open("r", encoding="utf-8") as file:
            for line in file:
                key, raw_value = line.split(":", maxsplit=1)
                value_kb = int(raw_value.strip().split()[0])
                values[key] = value_kb

        total_kb = values["MemTotal"]
        available_kb = values["MemAvailable"]

        used_percent = (
            (total_kb - available_kb) / total_kb * 100.0
        )

        if used_percent >= 95.0:
            state = "critical"
        elif used_percent >= 85.0:
            state = "high"
        else:
            state = "normal"

        return MemoryStatus(
            total_mb=round(total_kb / 1024),
            available_mb=round(available_kb / 1024),
            used_percent=round(used_percent, 1),
            state=state,
        )

    except Exception as exc:
        return MemoryStatus(
            total_mb=None,
            available_mb=None,
            used_percent=None,
            state="unknown",
            error=str(exc),
        )

def collect_disk_status(path: str = "/") -> DiskStatus:
    try:
        usage = shutil.disk_usage(path)
        used = usage.total - usage.free
        used_percent = used / usage.total * 100.0

        if used_percent >= 95.0:
            state = "critical"
        elif used_percent >= 85.0:
            state = "high"
        else:
            state = "normal"

        gb = 1024**3

        return DiskStatus(
            path=path,
            total_gb=round(usage.total / gb, 1),
            free_gb=round(usage.free / gb, 1),
            used_percent=round(used_percent, 1),
            state=state,
        )

    except Exception as exc:
        return DiskStatus(
            path=path,
            total_gb=None,
            free_gb=None,
            used_percent=None,
            state="unknown",
            error=str(exc),
        )

def collect_network_interface(
    name: str,
) -> NetworkInterfaceStatus:
    result = run(
        [
            "nmcli",
            "-t",
            "-f",
            "GENERAL.STATE,GENERAL.CONNECTION",
            "device",
            "show",
            name,
        ],
        timeout=5,
    )

    if result is None or result.returncode != 0:
        return NetworkInterfaceStatus(
            name=name,
            available=False,
            connected=False,
            state="unknown",
            connection=None,
            error="nmcli device query failed",
        )

    state = "unknown"
    connection = None

    for line in result.stdout.splitlines():
        if line.startswith("GENERAL.STATE:"):
            state = line.split(":", maxsplit=1)[1].strip()

        elif line.startswith("GENERAL.CONNECTION:"):
            value = line.split(":", maxsplit=1)[1].strip()
            connection = None if value == "--" else value

    connected = state.startswith("100")

    return NetworkInterfaceStatus(
        name=name,
        available=True,
        connected=connected,
        state=state,
        connection=connection,
    )

def collect_system_health() -> SystemHealthStatus:
    return SystemHealthStatus(
        temperature=collect_temperature_status(),
        throttling=collect_throttling_status(),
        memory=collect_memory_status(),
        disk=collect_disk_status("/"),
        ethernet=collect_network_interface("eth0"),
        wifi=collect_network_interface("wlan0"),
    )

def run(
    command: list[str],
    *,
    timeout: int = 5,
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

def main() -> int:
    import json

    status = collect_system_health()
    print(json.dumps(status.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
