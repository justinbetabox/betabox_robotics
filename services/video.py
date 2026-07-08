from __future__ import annotations

import argparse
import time
from pathlib import Path

from betabox_robotics.vision import VisionService, VisionServiceConfig

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8080
DEFAULT_FPS = 20

STATE_DIR = Path.home() / ".local" / "state" / "betabox"
LOG_FILE = STATE_DIR / "video.log"


def log(message: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    with LOG_FILE.open("a") as file:
        file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")


def run_video_service(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    fps: int = DEFAULT_FPS,
) -> int:
    config = VisionServiceConfig(host=host, port=port, fps=fps)
    service = VisionService(config)

    try:
        log(f"starting video service host={host} port={port} fps={fps}")
        service.run()
    except KeyboardInterrupt:
        log("video service interrupted")
    finally:
        log("stopping video service")
        service.stop()
        log("video service stopped")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="betabox video")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)

    args = parser.parse_args(argv)

    return run_video_service(
        host=args.host,
        port=args.port,
        fps=args.fps,
    )


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
