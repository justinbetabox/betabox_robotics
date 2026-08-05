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
            "Enable managed color detection and report "
            "visible colors through the BetaboxCar API."
        )
    )

    parser.add_argument(
        "--colors",
        nargs="+",
        default=[
            "red",
            "green",
            "blue",
        ],
        help=("Color names to enable. Default: red green blue."),
    )

    parser.add_argument(
        "--min-area",
        type=float,
        default=None,
        help=("Optional minimum detected area in pixels."),
    )

    parser.add_argument(
        "--duration",
        type=float,
        default=15.0,
        help=("How long to report detections in seconds. Default: 15."),
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=0.5,
        help=("Delay between reports in seconds. Default: 0.5."),
    )

    args = parser.parse_args(argv)

    if args.min_area is not None and args.min_area <= 0:
        parser.error("--min-area must be greater than zero")

    if args.duration <= 0:
        parser.error("--duration must be greater than zero")

    if args.interval <= 0:
        parser.error("--interval must be greater than zero")

    print("Betabox Car vision detection demo")
    print("=================================")
    print()
    print("Enabled colors: " + ", ".join(args.colors))

    detection_enabled = False

    try:
        with BetaboxCar() as car:
            print()
            print("Enabling color detection...")

            car.enable_color_detection(
                args.colors,
                min_area=args.min_area,
            )
            detection_enabled = True

            print("Waiting for detector metadata...")
            sleep(1.0)

            started_at = monotonic()

            while monotonic() - started_at < args.duration:
                colors = car.visible_colors()

                print()
                print("Visible colors: " + (", ".join(colors) if colors else "none"))

                for color in args.colors:
                    count = car.color_count(color)

                    if count == 0:
                        continue

                    center = car.color_center(color)
                    area = car.color_area(color)

                    print(
                        f"- {color}: "
                        f"count={count}, "
                        f"center={center}, "
                        f"largest_area={area}"
                    )

                sleep(args.interval)

            print()
            print("Disabling color detection...")
            car.disable_color_detection()
            detection_enabled = False

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
        print("Demo interrupted.")
        return 1

    except Exception as exc:
        logger.exception("Unexpected failure in vision detection demo.")
        print()
        print(f"Vision detection demo failed: {exc}")
        return 1

    finally:
        if detection_enabled:
            logger.warning(
                "Color detection may still be enabled; BetaboxCar cleanup completed."
            )

    print()
    print("Demo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
