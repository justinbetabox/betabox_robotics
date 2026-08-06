from __future__ import annotations

import argparse
import logging
import time

logger = logging.getLogger(__name__)

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.vision import (
    VisionService,
    VisionServiceConfig,
)


def _validate_string(
    value: object,
    *,
    name: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")

    result = value.strip()

    if not result:
        raise ValueError(f"{name} cannot be empty")

    return result


def _validate_port(
    value: object,
) -> int:
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError("port must be an integer")

    if not 1 <= value <= 65535:
        raise ValueError("port must be between 1 and 65535")

    return value


def _validate_fps(
    value: object,
) -> int:
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError("fps must be an integer")

    if value <= 0:
        raise ValueError("fps must be greater than 0")

    return value


def log(
    message: str,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> None:
    message_value = _validate_string(
        message,
        name="message",
    )

    if not isinstance(
        config,
        PlatformConfig,
    ):
        raise TypeError("config must be a PlatformConfig")

    try:
        config.paths.state_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        with config.paths.video_log.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message_value}\n")
    except OSError:
        # Logging failure should not prevent the video
        # service from starting or stopping.
        return


def run_video_service(
    *,
    host: str | None = None,
    port: int | None = None,
    fps: int | None = None,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> int:
    if not isinstance(
        config,
        PlatformConfig,
    ):
        raise TypeError("config must be a PlatformConfig")

    selected_host = _validate_string(
        (config.network.bind_host if host is None else host),
        name="host",
    )
    selected_port = _validate_port(config.network.vision_port if port is None else port)
    selected_fps = _validate_fps(config.runtime.vision_fps if fps is None else fps)

    vision_config = VisionServiceConfig(
        host=selected_host,
        port=selected_port,
        fps=selected_fps,
    )

    service = VisionService(vision_config)

    log(
        (
            "starting video service "
            f"host={selected_host} "
            f"port={selected_port} "
            f"fps={selected_fps}"
        ),
        config,
    )

    try:
        service.run()

    except KeyboardInterrupt:
        log(
            "video service interrupted",
            config,
        )

    except Exception as exc:
        log(
            f"video service failed: {exc}",
            config,
        )
        raise

    finally:
        log(
            "stopping video service",
            config,
        )

        try:
            service.stop()
        except Exception:
            logger.exception("Video service failed to stop cleanly.")
            log(
                "video service stop failed",
                config,
            )
        else:
            log(
                "video service stopped",
                config,
            )

    return 0


def main(
    argv: list[str] | None = None,
) -> int:
    config = DEFAULT_PLATFORM_CONFIG

    parser = argparse.ArgumentParser(prog="betabox video")

    parser.add_argument(
        "--host",
        default=config.network.bind_host,
    )
    parser.add_argument(
        "--port",
        type=int,
        default=config.network.vision_port,
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=config.runtime.vision_fps,
    )

    args = parser.parse_args(argv)

    try:
        return run_video_service(
            host=args.host,
            port=args.port,
            fps=args.fps,
            config=config,
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        print(exc)
        return 1


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
