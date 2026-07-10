from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

from betabox_robotics.services.status import collect_status

LOG_DIR = Path.home() / ".local" / "state" / "betabox"
LOG_FILE = LOG_DIR / "monitor.log"

DEFAULT_INTERVAL_SECONDS = 60


def log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    with LOG_FILE.open("a") as file:
        file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")


def collect_snapshot() -> dict:
    report = collect_status()
    return asdict(report)


def summarize(snapshot: dict) -> dict:
    hardware = snapshot.get("hardware", {})

    battery = hardware.get("battery", {})
    audio = hardware.get("audio", {})
    vision = hardware.get("vision", {})
    sensors = hardware.get("sensors", {})
    i2c = hardware.get("i2c", {})

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
    }


def run_once(previous_summary: dict | None = None) -> dict:
    snapshot = collect_snapshot()
    summary = summarize(snapshot)

    if previous_summary is None:
        log("monitor started")
        log("initial status: " + json.dumps(summary, sort_keys=True))
        return summary

    changes = find_changes(previous_summary, summary)

    for change in changes:
        log("status changed: " + change)

    return summary


def run_forever(interval_seconds: int = DEFAULT_INTERVAL_SECONDS) -> int:
    previous_summary: dict | None = None

    log(f"monitor loop starting interval={interval_seconds}s")

    while True:
        try:
            previous_summary = run_once(previous_summary)
        except Exception as exc:
            log(f"monitor error: {exc}")

        time.sleep(interval_seconds)

def find_changes(previous: dict, current: dict, prefix: str = "") -> list[str]:
    changes: list[str] = []

    keys = set(previous) | set(current)

    for key in sorted(keys):
        path = f"{prefix}.{key}" if prefix else key
        old = previous.get(key)
        new = current.get(key)

        if isinstance(old, dict) and isinstance(new, dict):
            changes.extend(find_changes(old, new, path))
        elif old != new:
            changes.append(f"{path}: {old!r} -> {new!r}")

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
