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
        print("No color metadata available yet.")
        return

    count = metadata.data.get(
        "count",
        len(metadata.detections),
    )
    counts = metadata.data.get(
        "counts",
        {},
    )

    print(f"Timestamp: {metadata.timestamp:.3f}")
    print(f"Detections: {count}")

    if isinstance(counts, dict):
        summary = ", ".join(f"{name}={value}" for name, value in counts.items())

        if summary:
            print(f"Counts: {summary}")

    if not metadata.detections:
        print("Objects: none")
        return

    print("Objects:")

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

        area = detection.data.get("area")

        if isinstance(area, int | float):
            details.append(f"area={area:.1f}")

        print(" | ".join(details))


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Enable color detection through the managed "
            "Betabox Vision service and print live metadata."
        )
    )

    parser.add_argument(
        "colors",
        nargs="*",
        default=[
            "red",
        ],
        help=("Colors to detect. Examples: red green blue yellow. Default: red."),
    )

    parser.add_argument(
        "--min-area",
        type=float,
        default=500.0,
        help=("Minimum detected region area in pixels. Default: 500."),
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
        help=("Leave color detection enabled after the demo exits."),
    )

    args = parser.parse_args(argv)

    if args.min_area < 0:
        parser.error("--min-area cannot be negative")

    if args.duration <= 0:
        parser.error("--duration must be greater than zero")

    if args.interval <= 0:
        parser.error("--interval must be greater than zero")

    client = VisionClient()
    enabled = False

    try:
        status = client.enable_color_detection(
            args.colors,
            min_area=args.min_area,
        )
        enabled = True

        print("Color detection enabled")
        print("-----------------------")
        print("Colors: " + ", ".join(args.colors))
        print(f"Minimum area: {args.min_area:.1f}")
        print(f"Detector enabled: {status.is_enabled('color')}")
        print()
        print(f"Reading metadata for {args.duration:.1f} seconds...")
        print()

        started_at = time.monotonic()
        sample_number = 0

        while time.monotonic() - started_at < args.duration:
            sample_number += 1

            print(f"Sample {sample_number}")
            print("-" * (len(str(sample_number)) + 7))

            metadata = client.metadata("color")

            print_metadata(metadata)
            print()

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print()
        print("Color detection demo interrupted.")

    except (
        TypeError,
        ValueError,
        VisionClientError,
    ) as exc:
        print(f"Unable to run color detection demo: {exc}")
        return 1

    finally:
        if enabled and not args.leave_enabled:
            try:
                client.disable_detection("color")
                print("Color detection disabled.")
            except VisionClientError as exc:
                print(f"Unable to disable color detection: {exc}")
                return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
