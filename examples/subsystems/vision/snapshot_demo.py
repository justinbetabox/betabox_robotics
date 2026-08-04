from __future__ import annotations

import argparse

from betabox_robotics.vision import (
    ClientSnapshot,
    VisionClient,
    VisionClientError,
)


def print_snapshot(
    snapshot: ClientSnapshot,
) -> None:
    print("Snapshot captured")
    print("-----------------")
    print(f"Path: {snapshot.path}")
    print(f"Format: {snapshot.format}")
    print(f"Timestamp: {snapshot.timestamp}")


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=("Capture a snapshot through the managed Betabox Vision service.")
    )

    parser.add_argument(
        "--filename",
        help=(
            "Output filename. Use .jpg, .jpeg, or .png. "
            "A timestamped JPEG name is generated when omitted."
        ),
    )

    parser.add_argument(
        "--overlay",
        action="store_true",
        help="Draw the latest detection metadata onto the snapshot.",
    )

    parser.add_argument(
        "--source",
        help=("Metadata source to use for the overlay, such as color or face."),
    )

    args = parser.parse_args(argv)

    if args.source is not None and not args.overlay:
        parser.error("--source requires --overlay")

    client = VisionClient()

    try:
        snapshot = client.snapshot(
            filename=args.filename,
            overlay=args.overlay,
            source=args.source,
        )
    except (
        TypeError,
        ValueError,
        VisionClientError,
    ) as exc:
        print(f"Unable to capture snapshot: {exc}")
        return 1

    print_snapshot(snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
