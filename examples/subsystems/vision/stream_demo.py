from __future__ import annotations

import argparse
import time

from betabox_robotics.vision import (
    ClientStreamOverlayStatus,
    VisionClient,
    VisionClientError,
)


def print_overlay_status(
    status: ClientStreamOverlayStatus,
) -> None:
    source = status.source if status.source is not None else "latest metadata"

    print(f"Overlay: {'enabled' if status.enabled else 'disabled'}")

    if status.enabled:
        print(f"Overlay source: {source}")


def print_stream_status(
    client: VisionClient,
) -> None:
    statistics = client.statistics()
    streaming = statistics.streaming

    print("Stream status")
    print("-------------")
    print(f"Running: {streaming.running}")
    print(f"Connected clients: {streaming.clients}")
    print(f"Frames received: {streaming.frames_received}")
    print(f"Frame available: {streaming.has_frame}")
    print_overlay_status(streaming.overlay)


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect the managed Betabox WebRTC stream "
            "and optionally control its detection overlay."
        )
    )

    overlay_group = parser.add_mutually_exclusive_group()

    overlay_group.add_argument(
        "--overlay",
        action="store_true",
        help="Enable metadata overlays on the stream.",
    )

    overlay_group.add_argument(
        "--disable-overlay",
        action="store_true",
        help="Disable stream overlays.",
    )

    parser.add_argument(
        "--source",
        help=("Metadata source used for the overlay, such as color or face."),
    )

    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help=("How long to monitor stream statistics. Default: 10 seconds."),
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help=("Delay between status updates. Default: 1 second."),
    )

    parser.add_argument(
        "--leave-overlay",
        action="store_true",
        help=(
            "Leave an overlay enabled when the demo exits. "
            "By default, an overlay enabled by this demo is removed."
        ),
    )

    args = parser.parse_args(argv)

    if args.source is not None and not args.overlay:
        parser.error("--source requires --overlay")

    if args.duration <= 0:
        parser.error("--duration must be greater than zero")

    if args.interval <= 0:
        parser.error("--interval must be greater than zero")

    client = VisionClient()
    overlay_enabled_by_demo = False
    exit_code = 0

    try:
        if args.overlay:
            status = client.enable_stream_overlay(args.source)
            overlay_enabled_by_demo = True

            print("Stream overlay enabled.")
            print_overlay_status(status)
            print()

        elif args.disable_overlay:
            status = client.disable_stream_overlay()

            print("Stream overlay disabled.")
            print_overlay_status(status)
            print()

        statistics = client.statistics()
        server = statistics.server

        display_host = "127.0.0.1" if server.host == "0.0.0.0" else server.host

        print("Betabox Vision WebRTC stream")
        print("============================")
        print("Open this address in a browser on the robot:")
        print(f"http://{display_host}:{server.port}/")
        print()
        print(
            "From another device, replace the host with "
            "the robot's hostname or IP address."
        )
        print()
        print(f"Monitoring for {args.duration:.1f} seconds...")
        print()

        started_at = time.monotonic()
        sample_number = 0

        while time.monotonic() - started_at < args.duration:
            sample_number += 1

            heading = f"Sample {sample_number}"

            print(heading)
            print("-" * len(heading))

            print_stream_status(client)
            print()

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print()
        print("Stream demo interrupted.")

    except (
        TypeError,
        ValueError,
        VisionClientError,
    ) as exc:
        print(f"Unable to run stream demo: {exc}")
        exit_code = 1

    finally:
        if overlay_enabled_by_demo and not args.leave_overlay:
            try:
                client.disable_stream_overlay()
                print("Stream overlay disabled.")
            except VisionClientError as exc:
                print(f"Unable to disable stream overlay: {exc}")
                exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
