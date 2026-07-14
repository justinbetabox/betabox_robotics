from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from typing import Literal

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.status import collect_status
from betabox_robotics.services.system_health import collect_system_health


DEFAULT_INTERVAL_SECONDS = 60

Severity = Literal["info", "warning", "error", "critical"]

@dataclass(frozen=True)
class MonitorEvent:
    timestamp: str
    severity: Severity
    component: str
    event: str
    previous: object
    current: object
    message: str

def timestamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")

def write_event(
    event: MonitorEvent,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> None:
    config.paths.state_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    with config.paths.events_file.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            json.dumps(
                asdict(event),
                sort_keys=True,
            )
            + "\n"
        )

    log(
        f"[{event.severity.upper()}] "
        f"{event.component}: {event.message}",
        config=config,
    )

def severity_for_change(
    path: str,
    previous: object,
    current: object,
) -> Severity:
    if path.endswith("battery_state"):
        if current == "critical":
            return "error"

        if current == "low":
            return "warning"

        return "info"

    if path.endswith(
        (
            "robot_available",
            "i2c_available",
            "audio_available",
            "vision_service_available",
            "vision_running",
            "camera_running",
            "camera_has_frame",
        )
    ):
        return "info" if current is True else "error"

    if path.endswith("grayscale_available"):
        return "info" if current is True else "warning"

    if path.startswith("services."):
        return "info" if current == "active" else "error"

    if path.endswith("temperature_state"):
        if current == "critical":
            return "critical"

        if current == "high":
            return "warning"

        return "info"

    if path.endswith("memory_state"):
        if current == "critical":
            return "critical"

        if current == "high":
            return "warning"

        return "info"

    if path.endswith("disk_state"):
        if current == "critical":
            return "critical"

        if current == "high":
            return "warning"

        return "info"

    if path.endswith("undervoltage_now"):
        return "critical" if current is True else "info"

    if path.endswith("throttled_now"):
        return "error" if current is True else "info"

    if path.endswith(
        (
            "undervoltage_occurred",
            "throttled_occurred",
        )
    ):
        return "warning" if current is True else "info"

    if path.endswith(
        (
            "ethernet_connected",
            "wifi_connected",
        )
    ):
        return "info" if current is True else "warning"

    return "info"

def message_for_change(
    path: str,
    previous: object,
    current: object,
) -> str:
    labels = {
        "hardware.robot_available": "Robot hardware",
        "hardware.i2c_available": "I²C bus",
        "hardware.battery_state": "Battery",
        "hardware.grayscale_available": "Grayscale sensor",
        "hardware.audio_available": "Audio device",
        "hardware.vision_service_available": "Vision service",
        "hardware.vision_running": "Vision runtime",
        "hardware.camera_running": "Camera",
        "hardware.camera_has_frame": "Camera frames",
        "system.temperature_state": "CPU temperature",
        "system.undervoltage_now": "Undervoltage",
        "system.undervoltage_occurred": "Historical undervoltage",
        "system.throttled_now": "CPU throttling",
        "system.throttled_occurred": "Historical throttling",
        "system.memory_state": "Memory usage",
        "system.disk_state": "Disk usage",
        "system.ethernet_connected": "Ethernet",
        "system.wifi_connected": "Wi-Fi",
    }

    label = labels.get(path, path)

    if isinstance(current, bool):
        if path.endswith("_connected"):
            state = "connected" if current else "disconnected"
        elif path.endswith("_now") or path.endswith("_occurred"):
            state = "detected" if current else "cleared"
        else:
            state = "available" if current else "unavailable"

        return f"{label} became {state}"

    return f"{label} changed from {previous!r} to {current!r}"

def log(
    message: str,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> None:
    config.paths.state_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    with config.paths.monitor_log.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} "
            f"{message}\n"
        )


def collect_snapshot() -> dict:
    status = collect_status()
    system_health = collect_system_health()

    snapshot = asdict(status)
    snapshot["system_health"] = system_health.to_dict()

    return snapshot


def summarize(snapshot: dict) -> dict:
    hardware = snapshot.get("hardware", {})
    system_health = snapshot.get("system_health", {})

    battery = hardware.get("battery", {})
    audio = hardware.get("audio", {})
    vision = hardware.get("vision", {})
    sensors = hardware.get("sensors", {})
    i2c = hardware.get("i2c", {})

    temperature = system_health.get("temperature", {})
    throttling = system_health.get("throttling", {})
    memory = system_health.get("memory", {})
    disk = system_health.get("disk", {})
    ethernet = system_health.get("ethernet", {})
    wifi = system_health.get("wifi", {})

    return {
        "services": snapshot.get("services", {}),
        "hardware": {
            "robot_available": hardware.get("robot_available"),
            "i2c_available": i2c.get("available"),
            "i2c_devices": i2c.get("devices", []),
            "battery_state": battery.get("state"),
            "grayscale_available": sensors.get("grayscale_available"),
            "audio_available": audio.get("available"),
            "vision_service_available": vision.get("service_available"),
            "vision_running": vision.get("running"),
            "camera_running": vision.get("camera_running"),
            "camera_has_frame": vision.get("camera_has_frame"),
        },
        "system": {
            "temperature_state": temperature.get("state"),
            "undervoltage_now": throttling.get("undervoltage_now"),
            "undervoltage_occurred": throttling.get("undervoltage_occurred"),
            "throttled_now": throttling.get("throttled_now"),
            "throttled_occurred": throttling.get("throttled_occurred"),
            "memory_state": memory.get("state"),
            "disk_state": disk.get("state"),
            "ethernet_connected": ethernet.get("connected"),
            "wifi_connected": wifi.get("connected"),
        },
    }


def run_once(
    previous_summary: dict | None = None,
    *,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> dict:
    snapshot = collect_snapshot()
    summary = summarize(snapshot)

    if previous_summary is None:
        log(
            "monitor started",
            config=config,
        )
        log(
            "initial status: "
            + json.dumps(summary, sort_keys=True),
            config=config,
        )
        return summary

    for path, previous, current in find_changes(
        previous_summary,
        summary,
    ):
        event = MonitorEvent(
            timestamp=timestamp(),
            severity=severity_for_change(
                path,
                previous,
                current,
            ),
            component=path.split(".")[0],
            event=path,
            previous=previous,
            current=current,
            message=message_for_change(
                path,
                previous,
                current,
            ),
        )

        write_event(
            event,
            config=config,
        )

    return summary


def run_forever(
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    *,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> int:
    previous_summary: dict | None = None

    log(
        f"monitor loop starting interval={interval_seconds}s",
        config=config,
    )

    while True:
        try:
            previous_summary = run_once(
                previous_summary,
                config=config,
            )
        except Exception as exc:
            log(
                f"monitor error: {exc}",
                config=config,
            )

        time.sleep(interval_seconds)

def find_changes(
    previous: dict,
    current: dict,
    prefix: str = "",
) -> list[tuple[str, object, object]]:
    changes: list[tuple[str, object, object]] = []

    keys = set(previous) | set(current)

    for key in sorted(keys):
        path = f"{prefix}.{key}" if prefix else key
        old = previous.get(key)
        new = current.get(key)

        if isinstance(old, dict) and isinstance(new, dict):
            changes.extend(find_changes(old, new, path))
        elif old != new:
            changes.append((path, old, new))

    return changes


def main(argv: list[str] | None = None) -> int:
    interval = DEFAULT_INTERVAL_SECONDS

    if argv:
        if "--once" in argv:
            run_once()
            return 0

        if "--interval" in argv:
            index = argv.index("--interval")
            try:
                interval = int(argv[index + 1])
            except Exception:
                print("Invalid --interval value")
                return 1

    return run_forever(interval)


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
