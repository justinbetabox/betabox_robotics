from __future__ import annotations

import json
import time
from pathlib import Path

from betabox_robotics.audio import Audio
from betabox_robotics.services.verify import collect_checks

LOG_DIR = Path.home() / ".local" / "state" / "betabox"
LOG_FILE = LOG_DIR / "boot_announce.log"


def log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a") as file:
        file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")


def say(audio: Audio, message: str) -> None:
    log(f"SAY: {message}")

    try:
        audio.say(message)
    except Exception as exc:
        log(f"audio failed: {exc}")


def summarize_checks() -> tuple[bool, dict[str, bool]]:
    checks = collect_checks(include_robot=True)

    results = {check.name: check.ok for check in checks}

    ready = all(results.values())

    log("Verification results: " + json.dumps(results, sort_keys=True))

    return ready, results


def main() -> int:
    log("Boot announcer started")

    try:
        audio = Audio()
    except Exception as exc:
        log(f"Audio initialization failed: {exc}")
        return 1

    try:
        say(audio, "Betabox starting")

        ready, results = summarize_checks()

        if ready:
            say(audio, "Ready for class")
            log("Boot announce complete: ready")
            return 0

        if not results.get("hardware:i2c", False):
            say(audio, "I two C failed")

        if not results.get("camera:picamera2", False):
            say(audio, "Camera failed")

        if not results.get("audio:hifiberry", False):
            say(audio, "Audio failed")

        if not results.get("audio:speech_backend", False):
            say(audio, "Speech failed")

        if not results.get("robot:construct", False):
            say(audio, "Robot failed")

        say(audio, "Teacher help needed")
        log("Boot announce complete: not ready")
        return 1

    finally:
        audio.close()


if __name__ == "__main__":
    raise SystemExit(main())
