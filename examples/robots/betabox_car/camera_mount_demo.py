from __future__ import annotations

import logging
from time import sleep

from betabox_robotics import (
    BetaboxCar,
    RobotBusyError,
)
from betabox_robotics.robots import RobotError

logger = logging.getLogger(__name__)


def print_status(
    car: BetaboxCar,
) -> None:
    status = car.camera_mount_status()

    print()
    print("Camera mount status")
    print("-------------------")

    for name, value in status.to_dict().items():
        print(f"{name}: {value}")


def main() -> int:
    print("Betabox Car camera mount demo")
    print("=============================")
    print()
    print(
        "The camera mount will move through several "
        "positions and then return to center."
    )

    try:
        with BetaboxCar() as car:
            print_status(car)

            print()
            print("Looking left...")
            car.camera_pan(
                -25,
                smooth=True,
            )
            sleep(1.0)

            print("Looking right...")
            car.camera_pan(
                25,
                smooth=True,
            )
            sleep(1.0)

            print("Looking up...")
            car.camera_tilt(
                -15,
                smooth=True,
            )
            sleep(1.0)

            print("Looking down...")
            car.camera_tilt(
                15,
                smooth=True,
            )
            sleep(1.0)

            print("Looking diagonally...")
            car.look(
                pan=-20,
                tilt=10,
                smooth=True,
            )
            sleep(1.0)

            print("Returning to center...")
            car.look_center(smooth=True)
            sleep(0.5)

            print_status(car)

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
        logger.exception("Unexpected failure in camera mount demo.")
        print()
        print(f"Camera mount demo failed: {exc}")
        return 1

    print()
    print("Demo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
