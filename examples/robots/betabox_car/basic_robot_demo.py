from __future__ import annotations

from time import sleep

from betabox_robotics import (
    BetaboxCar,
    RobotBusyError,
)
from betabox_robotics.robots import (
    RobotError,
)


def main() -> int:
    print("Betabox Car basic demo")
    print("======================")

    try:
        with BetaboxCar() as car:
            print()
            print("Robot started")
            print("Capabilities: " + ", ".join(car.capability_names()))

            print()
            print("Driving forward at 30%...")
            car.forward(30)
            sleep(1.0)

            print("Stopping...")
            car.stop()

            print()
            print("Reading distance...")
            distance = car.distance(samples=5)
            print(f"Distance: {distance:.2f} cm")

            print()
            print("Capturing snapshot...")
            snapshot = car.capture(filename="basic_robot.jpg")
            print(f"Snapshot saved: {snapshot.path}")

    except RobotBusyError as exc:
        print(f"Unable to acquire the robot hardware: {exc}")
        return 1

    except RobotError as exc:
        print(f"Robot operation failed: {exc}")
        return 1

    except KeyboardInterrupt:
        print()
        print("Demo interrupted.")
        return 1

    print()
    print("Demo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
