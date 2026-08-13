from __future__ import annotations

import argparse
import json
import time
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Literal, cast

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.status import collect_status
from betabox_robotics.services.system_health import collect_system_health

Severity = Literal["info", "warning", "error", "critical"]

SEVERITIES: frozenset[str] = frozenset(
    {
        "info",
        "warning",
        "error",
        "critical",
    }
)


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


def _validate_interval(
    value: object,
) -> int:
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError("interval_seconds must be an integer")

    if value <= 0:
        raise ValueError("interval_seconds must be greater than 0")

    return value


def _validate_mapping(
    value: object,
    *,
    name: str,
) -> Mapping[str, object]:
    mapping = _optional_mapping(
        value,
        name=name,
    )

    if mapping is None:
        raise TypeError(f"{name} must be a mapping")

    return mapping


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


def _optional_mapping(
    value: object,
    *,
    name: str,
) -> Mapping[str, object] | None:
    if not isinstance(
        value,
        Mapping,
    ):
        return None

    mapping = cast(
        Mapping[object, object],
        value,
    )

    for key in mapping:
        if not isinstance(
            key,
            str,
        ):
            raise TypeError(f"{name} keys must be strings")

    return cast(
        Mapping[str, object],
        mapping,
    )


@dataclass(frozen=True, slots=True)
class MonitorEvent:
    timestamp: str
    severity: Severity
    component: str
    event: str
    previous: object
    current: object
    message: str

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "timestamp",
            _validate_string(
                self.timestamp,
                name="timestamp",
            ),
        )

        severity = self.severity.strip().lower()

        if severity not in SEVERITIES:
            raise ValueError("severity must be one of: critical, error, info, warning")

        object.__setattr__(
            self,
            "severity",
            severity,
        )

        object.__setattr__(
            self,
            "component",
            _validate_string(
                self.component,
                name="component",
            ),
        )
        object.__setattr__(
            self,
            "event",
            _validate_string(
                self.event,
                name="event",
            ),
        )
        object.__setattr__(
            self,
            "message",
            _validate_string(
                self.message,
                name="message",
            ),
        )


def timestamp() -> str:
    value = time.strftime("%Y-%m-%d %H:%M:%S")

    return _validate_string(
        value,
        name="timestamp",
    )


def write_event(
    event: MonitorEvent,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> None:
    config_value = _validate_config(config)

    config_value.paths.state_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    with config_value.paths.events_file.open(
        "a",
        encoding="utf-8",
    ) as file:
        _ = file.write(
            json.dumps(
                asdict(event),
                sort_keys=True,
            )
            + "\n"
        )

    log(
        (f"[{event.severity.upper()}] {event.component}: {event.message}"),
        config=config_value,
    )


def severity_for_change(
    path: str,
    current: object,
) -> Severity:
    path_value = _validate_string(
        path,
        name="path",
    )

    if path_value.endswith("battery_state"):
        if current == "critical":
            return "error"

        if current == "low":
            return "warning"

        return "info"

    if path_value.endswith(
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

    if path_value.endswith("grayscale_available"):
        return "info" if current is True else "warning"

    if path_value.startswith("services."):
        return "info" if current == "active" else "error"

    if path_value.endswith(
        (
            "temperature_state",
            "memory_state",
            "disk_state",
        )
    ):
        if current == "critical":
            return "critical"

        if current == "high":
            return "warning"

        return "info"

    if path_value.endswith("undervoltage_now"):
        return "critical" if current is True else "info"

    if path_value.endswith("throttled_now"):
        return "error" if current is True else "info"

    if path_value.endswith(
        (
            "undervoltage_occurred",
            "throttled_occurred",
        )
    ):
        return "warning" if current is True else "info"

    if path_value.endswith(
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
    path_value = _validate_string(
        path,
        name="path",
    )

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

    label = labels.get(
        path_value,
        path_value,
    )

    if isinstance(
        current,
        bool,
    ):
        if path_value.endswith("_connected"):
            state = "connected" if current else "disconnected"
        elif path_value.endswith(
            (
                "_now",
                "_occurred",
            )
        ):
            state = "detected" if current else "cleared"
        else:
            state = "available" if current else "unavailable"

        return f"{label} became {state}"

    return f"{label} changed from {previous!r} to {current!r}"


def log(
    message: str,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> None:
    message_value = _validate_string(
        message,
        name="message",
    )
    config_value = _validate_config(config)

    config_value.paths.state_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    with config_value.paths.monitor_log.open(
        "a",
        encoding="utf-8",
    ) as file:
        _ = file.write(f"{timestamp()} {message_value}\n")


def collect_snapshot(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> dict[str, object]:
    config_value = _validate_config(config)

    status = collect_status(config_value)
    system_health = collect_system_health(config_value)

    snapshot = asdict(status)
    snapshot["system_health"] = system_health.to_dict()

    return snapshot


def summarize(
    snapshot: Mapping[str, object],
) -> dict[str, object]:
    snapshot_value = _validate_mapping(
        snapshot,
        name="snapshot",
    )

    hardware = _validate_mapping(
        snapshot_value.get(
            "hardware",
            {},
        ),
        name="snapshot hardware",
    )

    system_health = _validate_mapping(
        snapshot_value.get(
            "system_health",
            {},
        ),
        name="snapshot system_health",
    )

    battery = _validate_mapping(
        hardware.get(
            "battery",
            {},
        ),
        name="battery",
    )

    audio = _validate_mapping(
        hardware.get(
            "audio",
            {},
        ),
        name="audio",
    )

    vision = _validate_mapping(
        hardware.get(
            "vision",
            {},
        ),
        name="vision",
    )

    sensors = _validate_mapping(
        hardware.get(
            "sensors",
            {},
        ),
        name="sensors",
    )

    i2c = _validate_mapping(
        hardware.get(
            "i2c",
            {},
        ),
        name="i2c",
    )

    temperature = _validate_mapping(
        system_health.get(
            "temperature",
            {},
        ),
        name="temperature",
    )

    throttling = _validate_mapping(
        system_health.get(
            "throttling",
            {},
        ),
        name="throttling",
    )

    memory = _validate_mapping(
        system_health.get(
            "memory",
            {},
        ),
        name="memory",
    )

    disk = _validate_mapping(
        system_health.get(
            "disk",
            {},
        ),
        name="disk",
    )

    ethernet = _validate_mapping(
        system_health.get(
            "ethernet",
            {},
        ),
        name="ethernet",
    )

    wifi = _validate_mapping(
        system_health.get(
            "wifi",
            {},
        ),
        name="wifi",
    )

    services = _validate_mapping(
        snapshot_value.get(
            "services",
            {},
        ),
        name="snapshot services",
    )

    return {
        "services": dict(services),
        "hardware": {
            "robot_available": hardware.get("passive_hardware_available"),
            "i2c_available": i2c.get("available"),
            "i2c_devices": i2c.get(
                "devices",
                [],
            ),
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
    previous_summary: Mapping[str, object] | None = None,
    *,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> dict[str, object]:
    config_value = _validate_config(config)

    if previous_summary is not None:
        previous_value = _validate_mapping(
            previous_summary,
            name="previous_summary",
        )
    else:
        previous_value = None

    snapshot = collect_snapshot(config_value)
    summary = summarize(snapshot)

    if previous_value is None:
        log(
            "monitor started",
            config=config_value,
        )
        log(
            (
                "initial status: "
                + json.dumps(
                    summary,
                    sort_keys=True,
                )
            ),
            config=config_value,
        )
        return summary

    for path, previous, current in find_changes(
        previous_value,
        summary,
    ):
        event = MonitorEvent(
            timestamp=timestamp(),
            severity=severity_for_change(
                path,
                current,
            ),
            component=path.split(
                ".",
                maxsplit=1,
            )[0],
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
            config=config_value,
        )

    return summary


def run_forever(
    interval_seconds: int | None = None,
    *,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> int:
    config_value = _validate_config(config)

    selected_interval = (
        config_value.monitoring.interval_seconds
        if interval_seconds is None
        else interval_seconds
    )
    interval_value = _validate_interval(selected_interval)

    previous_summary: dict[str, object] | None = None

    log(
        (f"monitor loop starting interval={interval_value}s"),
        config=config_value,
    )

    while True:
        try:
            previous_summary = run_once(
                previous_summary,
                config=config_value,
            )
        except (
            OSError,
            TypeError,
            ValueError,
            RuntimeError,
        ) as exc:
            try:
                log(
                    f"monitor error: {exc}",
                    config=config_value,
                )
            except OSError:
                pass

        time.sleep(interval_value)


def find_changes(
    previous: Mapping[str, object],
    current: Mapping[str, object],
    prefix: str = "",
) -> list[
    tuple[
        str,
        object,
        object,
    ]
]:
    previous_value = _validate_mapping(
        previous,
        name="previous",
    )
    current_value = _validate_mapping(
        current,
        name="current",
    )

    prefix_value = prefix.strip()

    changes: list[
        tuple[
            str,
            object,
            object,
        ]
    ] = []

    keys = set(previous_value) | set(current_value)

    for key in sorted(
        keys,
        key=str,
    ):
        path = f"{prefix_value}.{key}" if prefix_value else key

        old = cast(
            object,
            previous_value.get(key),
        )

        new = cast(
            object,
            current_value.get(key),
        )

        old_mapping = _optional_mapping(
            old,
            name=f"{path} previous",
        )

        new_mapping = _optional_mapping(
            new,
            name=f"{path} current",
        )

        if old_mapping is not None and new_mapping is not None:
            changes.extend(
                find_changes(
                    old_mapping,
                    new_mapping,
                    path,
                )
            )

        elif old != new:
            changes.append(
                (
                    path,
                    old,
                    new,
                )
            )

    return changes


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="betabox monitor",
    )

    _ = parser.add_argument(
        "--once",
        action="store_true",
        help="Run one monitoring pass and exit",
    )
    _ = parser.add_argument(
        "--interval",
        type=int,
        help="Monitoring interval in seconds",
    )

    return parser


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    return _build_parser().parse_args(argv)


def main(
    argv: list[str] | None = None,
) -> int:
    config = DEFAULT_PLATFORM_CONFIG
    args = parse_args(argv)

    try:
        once = _validate_flag(
            cast(
                object,
                args.once,
            ),
            name="once",
        )

        raw_interval = cast(
            object,
            args.interval,
        )

        interval = (
            config.monitoring.interval_seconds
            if raw_interval is None
            else _validate_interval(raw_interval)
        )

        if once:
            _ = run_once(
                config=config,
            )
            return 0

        return run_forever(
            interval,
            config=config,
        )

    except (
        TypeError,
        ValueError,
        OSError,
        RuntimeError,
    ) as exc:
        print(f"monitor failed: {exc}")
        return 1


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
