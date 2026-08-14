from __future__ import annotations

import json
import time

from betabox_robotics.audio import Audio
from betabox_robotics.audio.exceptions import AudioError
from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.robots import BETABOX_CAR
from betabox_robotics.services.verify_checks import (
    collect_checks,
)

FAILURE_ANNOUNCEMENTS: tuple[
    tuple[str, str],
    ...,
] = (
    (
        "hardware:i2c",
        "I two C failed",
    ),
    (
        "camera:picamera2",
        "Camera failed",
    ),
    (
        "audio:hifiberry",
        "Audio failed",
    ),
    (
        "audio:speech_backend",
        "Speech failed",
    ),
    (
        "robot:construct",
        "Robot failed",
    ),
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


def _validate_audio(
    value: object,
) -> Audio:
    if not isinstance(
        value,
        Audio,
    ):
        raise TypeError("audio must be an Audio")

    return value


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

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    with config_value.paths.boot_announce_log.open(
        "a",
        encoding="utf-8",
    ) as file:
        _ = file.write(f"{timestamp} {message_value}\n")


def say(
    audio: Audio,
    message: str,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> bool:
    audio_value = _validate_audio(audio)
    message_value = _validate_string(
        message,
        name="message",
    )
    config_value = _validate_config(config)

    log(
        f"SAY: {message_value}",
        config_value,
    )

    try:
        audio_value.say(message_value)
    except AudioError as exc:
        log(
            f"audio failed: {exc}",
            config_value,
        )
        return False

    return True


def summarize_checks(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> tuple[
    bool,
    dict[str, bool],
]:
    config_value = _validate_config(config)

    checks = collect_checks(
        include_robot=True,
        config=config_value,
    )

    results = {check.name: check.ok for check in checks}
    ready = bool(results) and all(results.values())

    log(
        (
            "Verification results: "
            + json.dumps(
                results,
                sort_keys=True,
            )
        ),
        config_value,
    )

    return (
        ready,
        results,
    )


def announce_failures(
    audio: Audio,
    results: dict[str, bool],
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> None:
    audio_value = _validate_audio(audio)
    config_value = _validate_config(config)

    for check_name, message in FAILURE_ANNOUNCEMENTS:
        if not results.get(
            check_name,
            False,
        ):
            _ = say(
                audio_value,
                message,
                config_value,
            )


def close_audio(
    audio: Audio,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> bool:
    audio_value = _validate_audio(audio)
    config_value = _validate_config(config)

    try:
        audio_value.close()
    except (
        AudioError,
        OSError,
    ) as exc:
        try:
            log(
                f"Audio cleanup failed: {exc}",
                config_value,
            )
        except OSError:
            pass

        return False

    return True


def main() -> int:
    config = DEFAULT_PLATFORM_CONFIG

    try:
        log(
            "Boot announcer started",
            config,
        )
    except OSError:
        return 1

    try:
        audio = Audio.default(BETABOX_CAR.audio)
    except (
        AudioError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        try:
            log(
                f"Audio initialization failed: {exc}",
                config,
            )
        except OSError:
            pass

        return 1

    result = 1

    try:
        _ = say(
            audio,
            "Betabox starting",
            config,
        )

        ready, results = summarize_checks(config)

        if ready:
            _ = say(
                audio,
                "Ready for use",
                config,
            )
            log(
                "Boot announce complete: ready",
                config,
            )
            result = 0
        else:
            announce_failures(
                audio,
                results,
                config,
            )
            _ = say(
                audio,
                "Troubleshooting needed",
                config,
            )
            log(
                "Boot announce complete: not ready",
                config,
            )
            result = 0

    except (
        AudioError,
        OSError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as exc:
        try:
            log(
                f"Boot announce failed: {exc}",
                config,
            )
        except OSError:
            pass

        result = 1

    finally:
        if not close_audio(
            audio,
            config,
        ):
            result = 1

    return result


if __name__ == "__main__":
    raise SystemExit(main())
