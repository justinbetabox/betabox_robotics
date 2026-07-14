from __future__ import annotations

import json
import time

from betabox_robotics.robots import BETABOX_CAR
from betabox_robotics.audio import Audio
from betabox_robotics.services.verify import collect_checks
from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)

def log(
    message: str,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> None:
    config.paths.state_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    with config.paths.boot_announce_log.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} "
            f"{message}\n"
        )


def say(
    audio: Audio,
    message: str,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> None:
    log(
        f"SAY: {message}",
        config,
    )

    try:
        audio.say(message)
    except Exception as exc:
        log(
            f"audio failed: {exc}",
            config,
        )


def summarize_checks(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> tuple[bool, dict[str, bool]]:
    checks = collect_checks(
        include_robot=True,
        config=config,
    )

    results = {
        check.name: check.ok
        for check in checks
    }

    ready = all(results.values())

    log(
        (
            "Verification results: "
            + json.dumps(
                results,
                sort_keys=True,
            )
        ),
        config,
    )

    return ready, results


def main() -> int:
    config = DEFAULT_PLATFORM_CONFIG

    log(
        "Boot announcer started",
        config,
    )

    try:
        audio = Audio.default(BETABOX_CAR.audio)
    except Exception as exc:
        log(
            f"Audio initialization failed: {exc}",
            config,
        )
        return 1

    try:
        say(audio, "Betabox starting", config)

        ready, results = summarize_checks(config)

        if ready:
            say(audio, "Ready for class", config)
            log("Boot announce complete: ready", config)
            return 0

        if not results.get("hardware:i2c", False):
            say(audio, "I two C failed", config)

        if not results.get("camera:picamera2", False):
            say(audio, "Camera failed", config)

        if not results.get("audio:hifiberry", False):
            say(audio, "Audio failed", config)

        if not results.get("audio:speech_backend", False):
            say(audio, "Speech failed", config)

        if not results.get("robot:construct", False):
            say(audio, "Robot failed", config)

        say(audio, "Teacher help needed", config)
        log("Boot announce complete: not ready", config)
        return 1

    finally:
        audio.close()


if __name__ == "__main__":
    raise SystemExit(main())
