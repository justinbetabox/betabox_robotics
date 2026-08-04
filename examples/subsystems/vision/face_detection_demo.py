from __future__ import annotations

import argparse
import time

from betabox_robotics.vision import (
    ClientMetadata,
    VisionClient,
    VisionClientError,
)


def print_metadata(
    metadata: ClientMetadata | None,
) -> None:
    if metadata is None:
        print("No face metadata available yet.")
        return

    count = metadata.data.get(
        "count",
        len(metadata.detections),
    )

    print(f"Timestamp: {metadata.timestamp:.3f}")
    print(f"Faces detected: {count}")

    if not metadata.detections:
        print("Faces: none")
        return

    print("Faces:")

    for index, detection in enumerate(
        metadata.detections,
        start=1,
    ):
        details = [
            f"{index}. {detection.label}",
        ]

        if detection.box is not None:
            x, y, width, height = detection.box

            details.append(f"box=({x}, {y}, {width}, {height})")

        if detection.center is not None:
            center_x, center_y = detection.center

            details.append(f"center=({center_x}, {center_y})")

        width = detection.data.get("width")
        height = detection.data.get("height")

        if (
            isinstance(width, int)
            and not isinstance(width, bool)
            and isinstance(height, int)
            and not isinstance(height, bool)
        ):
            details.append(f"size={width}x{height}")

        print(" | ".join(details))


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Enable face detection through the managed "
            "Betabox Vision service and print live metadata."
        )
    )

    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help=("How long to print detection results in seconds. Default: 10."),
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=0.5,
        help=("Delay between metadata reads in seconds. Default: 0.5."),
    )

    parser.add_argument(
        "--leave-enabled",
        action="store_true",
        help=("Leave face detection enabled after the demo exits."),
    )

    args = parser.parse_args(argv)

    if args.duration <= 0:
        parser.error("--duration must be greater than zero")

    if args.interval <= 0:
        parser.error("--interval must be greater than zero")

    client = VisionClient()
    enabled = False
    exit_code = 0

    try:
        status = client.enable_detection("face")
        enabled = True

        print("Face detection enabled")
        print("----------------------")
        print(f"Detector enabled: {status.is_enabled('face')}")
        print()
        print(f"Reading metadata for {args.duration:.1f} seconds...")
        print()

        started_at = time.monotonic()
        sample_number = 0

        while time.monotonic() - started_at < args.duration:
            sample_number += 1

            heading = f"Sample {sample_number}"

            print(heading)
            print("-" * len(heading))

            metadata = client.metadata("face")

            print_metadata(metadata)
            print()

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print()
        print("Face detection demo interrupted.")

    except (
        TypeError,
        ValueError,
        VisionClientError,
    ) as exc:
        print(f"Unable to run face detection demo: {exc}")
        exit_code = 1

    finally:
        if enabled and not args.leave_enabled:
            try:
                client.disable_detection("face")
                print("Face detection disabled.")
            except VisionClientError as exc:
                print(f"Unable to disable face detection: {exc}")
                exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
