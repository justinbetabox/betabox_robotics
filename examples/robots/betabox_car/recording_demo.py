from __future__ import annotations

import argparse
import logging
from time import monotonic, sleep

from betabox_robotics import (
    BetaboxCar,
    RobotBusyError,
)
from betabox_robotics.robots import RobotError

logger = logging.getLogger(__name__)


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Record video through the managed Betabox "
            "Vision service using the BetaboxCar API."
        )
    )

    parser.add_argument(
        "--duration",
        type=float,
        default=5.0,
        help=("Recording duration in seconds. Default: 5."),
    )

    parser.add_argument(
        "--filename",
        help=("Optional output filename. The Vision service normalizes the extension."),
    )

    parser.add_argument(
        "--overlay",
        action="store_true",
        help=("Draw detection metadata onto the recording."),
    )

    parser.add_argument(
        "--source",
        help=("Metadata source for the overlay, such as color or face."),
    )

    args = parser.parse_args(argv)

    if args.duration <= 0:
        parser.error("--duration must be greater than zero")

    if args.source is not None and not args.overlay:
        parser.error("--source requires --overlay")

    print("Betabox Car recording demo")
    print("==========================")

    recording_started = False

    try:
        with BetaboxCar() as car:
            detection_enabled = False

            if args.source == "color":
                print()
                print("Enabling color detection...")

                car.enable_color_detection()
                detection_enabled = True

            try:
                output_path = car.start_recording(
                    filename=args.filename,
                    overlay=args.overlay,
                    source=args.source,
                )
                recording_started = True

                print()
                print("Recording started")
                print(f"Planned output: {output_path}")
                print(f"Recording for {args.duration:.2f} seconds...")

                started_at = monotonic()

                while True:
                    elapsed = monotonic() - started_at

                    if elapsed >= args.duration:
                        break

                    sleep(
                        min(
                            0.1,
                            args.duration - elapsed,
                        )
                    )

                recording = car.stop_recording()
                recording_started = False

            finally:
                if detection_enabled:
                    try:
                        car.disable_color_detection()
                    except Exception:
                        logger.exception("Failed to disable color detection.")

            print()
            print("Recording complete")
            print("------------------")
            print(f"Path: {recording.path}")
            print(f"Duration: {recording.duration:.2f} seconds")
            print(f"Frames: {recording.frame_count}")
            print(f"FPS: {recording.fps}")
            print(f"Started: {recording.start_timestamp}")
            print(f"Ended: {recording.end_timestamp}")

    except RobotBusyError as exc:
        print()
        print(f"Unable to acquire the robot hardware: {exc}")
        return 1

    except RobotError as exc:
        print()
        print(f"Robot operation failed: {exc}")
        return 1

    except KeyboardInterrupt:
        print()
        print("Recording interrupted.")
        return 1

    except Exception as exc:
        logger.exception("Unexpected failure in recording demo.")
        print()
        print(f"Recording demo failed: {exc}")
        return 1

    finally:
        if recording_started:
            logger.warning("Recording cleanup was delegated to BetaboxCar.stop_all().")

    print()
    print("Demo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
