from __future__ import annotations

import argparse
import time

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.vision import (
    VisionService,
    VisionServiceConfig,
)


def log(
    message: str,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> None:
    config.paths.state_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    with config.paths.video_log.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} "
            f"{message}\n"
        )


def run_video_service(
    *,
    host: str | None = None,
    port: int | None = None,
    fps: int | None = None,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> int:
    selected_host = (
        config.network.bind_host
        if host is None
        else host
    )

    selected_port = (
        config.network.vision_port
        if port is None
        else port
    )

    selected_fps = (
        config.runtime.vision_fps
        if fps is None
        else fps
    )

    if not selected_host:
        raise ValueError("host cannot be empty")

    if not 1 <= selected_port <= 65535:
        raise ValueError(
            "port must be between 1 and 65535"
        )

    if selected_fps <= 0:
        raise ValueError(
            "fps must be greater than 0"
        )

    vision_config = VisionServiceConfig(
        host=selected_host,
        port=selected_port,
        fps=selected_fps,
    )

    service = VisionService(vision_config)

    try:
        log(
            (
                "starting video service "
                f"host={selected_host} "
                f"port={selected_port} "
                f"fps={selected_fps}"
            ),
            config,
        )

        service.run()

    except KeyboardInterrupt:
        log(
            "video service interrupted",
            config,
        )

    finally:
        log(
            "stopping video service",
            config,
        )

        service.stop()

        log(
            "video service stopped",
            config,
        )

    return 0


def main(
    argv: list[str] | None = None,
) -> int:
    config = DEFAULT_PLATFORM_CONFIG

    parser = argparse.ArgumentParser(
        prog="betabox video"
    )

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

    if not args.host:
        print("--host cannot be empty")
        return 1

    if not 1 <= args.port <= 65535:
        print("--port must be between 1 and 65535")
        return 1

    if args.fps <= 0:
        print("--fps must be greater than 0")
        return 1

    return run_video_service(
        host=args.host,
        port=args.port,
        fps=args.fps,
        config=config,
    )


if __name__ == "__main__":
    import sys

    raise SystemExit(
        main(sys.argv[1:])
    )
