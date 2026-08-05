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
            "Drive forward until the ultrasonic sensor "
            "detects an obstacle within a configured distance."
        )
    )

    parser.add_argument(
        "--speed",
        type=float,
        default=20.0,
        help=("Forward speed percentage. Default: 20."),
    )

    parser.add_argument(
        "--stop-distance",
        type=float,
        default=25.0,
        help=(
            "Stop when an obstacle is this many "
            "centimeters away or closer. Default: 25."
        ),
    )

    parser.add_argument(
        "--samples",
        type=int,
        default=3,
        help=("Ultrasonic samples per reading. Default: 3."),
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=0.1,
        help=("Delay between readings in seconds. Default: 0.1."),
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help=("Maximum drive time in seconds. Default: 15."),
    )

    args = parser.parse_args(argv)

    if not 0 < args.speed <= 100:
        parser.error("--speed must be greater than 0 and no more than 100")

    if args.stop_distance <= 0:
        parser.error("--stop-distance must be greater than zero")

    if args.samples < 1:
        parser.error("--samples must be at least 1")

    if args.interval <= 0:
        parser.error("--interval must be greater than zero")

    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")

    print("Betabox Car sensor reaction demo")
    print("================================")
    print()
    print(
        "The robot will drive forward and stop when "
        f"an obstacle is within {args.stop_distance:.1f} cm."
    )
    print(f"Maximum drive time: {args.timeout:.1f} seconds")

    try:
        with BetaboxCar() as car:
            started_at = monotonic()

            print()
            print(f"Driving forward at {args.speed:.1f}%...")
            car.forward(args.speed)

            try:
                while True:
                    elapsed = monotonic() - started_at

                    if elapsed >= args.timeout:
                        print()
                        print("Timeout reached. Stopping.")
                        break

                    distance = car.distance(samples=args.samples)

                    print(f"Distance: {distance:.2f} cm")

                    if distance <= args.stop_distance:
                        print()
                        print("Obstacle detected. Stopping.")
                        break

                    sleep(args.interval)

            finally:
                car.stop()

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
        logger.exception("Unexpected failure in sensor reaction demo.")
        print()
        print(f"Sensor reaction demo failed: {exc}")
        return 1

    print()
    print("Demo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
