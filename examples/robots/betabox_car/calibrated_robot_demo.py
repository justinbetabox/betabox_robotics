from __future__ import annotations

import argparse
import logging
from pathlib import Path
from time import sleep

from betabox_robotics import (
    BetaboxCar,
    RobotBusyError,
)
from betabox_robotics.calibration import (
    CalibrationManager,
)
from betabox_robotics.robots import (
    RobotError,
)

logger = logging.getLogger(__name__)


def print_calibration_summary(
    manager: CalibrationManager,
) -> None:
    calibration = manager.load()

    print()
    print("Loaded calibration")
    print("------------------")
    print(f"Steering offset: {calibration.steering.offset:.2f}")
    print(f"Left motor trim: {calibration.motors.left_trim:.2f}")
    print(f"Right motor trim: {calibration.motors.right_trim:.2f}")
    print(f"Camera pan offset: {calibration.camera_mount.pan_offset:.2f}")
    print(f"Camera tilt offset: {calibration.camera_mount.tilt_offset:.2f}")
    print(f"Grayscale calibrated: {calibration.grayscale.calibrated}")


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=("Load saved calibration and construct a calibrated BetaboxCar.")
    )

    parser.add_argument(
        "--calibration-file",
        type=Path,
        required=True,
        help=("Path to the saved robot calibration JSON file."),
    )

    parser.add_argument(
        "--drive-test",
        action="store_true",
        help=(
            "Briefly drive forward to demonstrate "
            "the loaded motor and steering calibration."
        ),
    )

    parser.add_argument(
        "--speed",
        type=float,
        default=20.0,
        help=("Drive-test speed percentage. Default: 20."),
    )

    parser.add_argument(
        "--duration",
        type=float,
        default=1.0,
        help=("Drive-test duration in seconds. Default: 1."),
    )

    args = parser.parse_args(argv)

    if not 0 < args.speed <= 100:
        parser.error("--speed must be greater than 0 and no more than 100")

    if args.duration <= 0:
        parser.error("--duration must be greater than zero")

    manager = CalibrationManager(args.calibration_file)

    print("Betabox Car calibrated robot demo")
    print("=================================")
    print()
    print(f"Calibration file: {manager.calibration_file}")
    print(f"Saved calibration exists: {manager.exists()}")

    try:
        calibration = manager.load()

        print_calibration_summary(manager)

        with BetaboxCar(calibration=calibration) as car:
            print()
            print("Calibrated robot started.")

            print()
            print("Drive status")
            print("------------")

            for name, value in car.drive_status().to_dict().items():
                print(f"{name}: {value}")

            print(f"Camera mount status: {car.camera_mount_status().to_dict()}")

            if args.drive_test:
                print()
                print(
                    "Driving forward at "
                    f"{args.speed:.1f}% for "
                    f"{args.duration:.2f} seconds..."
                )

                car.forward(args.speed)

                try:
                    sleep(args.duration)
                finally:
                    car.stop()

                print("Drive test complete.")

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
        logger.exception("Unexpected failure in calibrated robot demo.")
        print()
        print(f"Calibrated robot demo failed: {exc}")
        return 1

    print()
    print("Demo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
