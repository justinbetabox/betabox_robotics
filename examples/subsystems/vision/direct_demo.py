from __future__ import annotations

import argparse
import time
from pathlib import Path

from betabox_robotics.vision import (
    FrameSourceError,
    Snapshot,
    SnapshotError,
    Vision,
)


def print_snapshot(
    snapshot: Snapshot,
) -> None:
    print()
    print("Snapshot captured")
    print("-----------------")
    print(f"Path: {snapshot.path}")
    print(f"Format: {snapshot.format}")
    print(f"Timestamp: {snapshot.timestamp}")


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Open the camera directly through the Vision subsystem. "
            "The managed betabox-video.service must be stopped first."
        )
    )

    parser.add_argument(
        "--duration",
        type=float,
        default=5.0,
        help=("How long to observe the direct frame pipeline. Default: 5 seconds."),
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help=("Delay between status updates. Default: 1 second."),
    )

    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Capture a snapshot before shutting down.",
    )

    parser.add_argument(
        "--filename",
        help=(
            "Snapshot filename. Use .jpg, .jpeg, or .png. "
            "A timestamped filename is generated when omitted."
        ),
    )

    parser.add_argument(
        "--directory",
        type=Path,
        help=("Snapshot output directory. Default: ~/media/pictures."),
    )

    args = parser.parse_args(argv)

    if args.duration <= 0:
        parser.error("--duration must be greater than zero")

    if args.interval <= 0:
        parser.error("--interval must be greater than zero")

    if args.filename is not None and not args.snapshot:
        parser.error("--filename requires --snapshot")

    if args.directory is not None and not args.snapshot:
        parser.error("--directory requires --snapshot")

    print("Direct Vision demo")
    print("==================")
    print("This process will open the physical camera directly.")
    print("Make sure betabox-video.service is stopped.")
    print()

    try:
        with Vision() as vision:
            print("Vision pipeline started.")
            print(f"Configured FPS: {vision.frame_source.fps}")
            print(f"Consumers: {vision.frame_source.consumer_count()}")
            print()

            started_at = time.monotonic()
            sample_number = 0

            while time.monotonic() - started_at < args.duration:
                sample_number += 1

                statistics = vision.frame_source.statistics()

                capture = statistics.get(
                    "capture",
                    {},
                )
                publish = statistics.get(
                    "publish",
                    {},
                )

                print(f"Sample {sample_number}")
                print(f"  Running: {vision.is_running()}")
                print(f"  Frame available: {statistics['has_frame']}")
                print(f"  Frame fresh: {statistics['frame_fresh']}")
                print(f"  Captured frames: {capture.get('count', 0)}")
                print(f"  Published frames: {publish.get('count', 0)}")
                print(f"  Frame age: {statistics['frame_age_seconds']}")
                print(f"  Last error: {statistics['last_error'] or 'none'}")
                print()

                time.sleep(args.interval)

            if args.snapshot:
                snapshot = vision.snapshot.capture(
                    filename=args.filename,
                    directory=args.directory,
                )

                print_snapshot(snapshot)

    except KeyboardInterrupt:
        print()
        print("Direct Vision demo interrupted.")
        return 0

    except (
        FrameSourceError,
        SnapshotError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"Unable to run direct Vision demo: {exc}")
        print()
        print("Check whether betabox-video.service still owns the camera.")
        return 1

    print()
    print("Vision pipeline stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
