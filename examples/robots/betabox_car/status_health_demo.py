from __future__ import annotations

import logging
from typing import Any

from betabox_robotics import (
    BetaboxCar,
    RobotBusyError,
)
from betabox_robotics.robots import (
    HealthCheck,
    RobotError,
    RobotHealth,
)

logger = logging.getLogger(__name__)


def print_mapping(
    title: str,
    value: dict[str, Any],
) -> None:
    print()
    print(title)
    print("-" * len(title))

    for name, item in value.items():
        print(f"{name}: {item}")


def print_health_check(
    check: HealthCheck,
) -> None:
    state = "OK" if check.ok else "FAILED"

    print(f"- {check.name}: {state}")

    if check.message:
        print(f"  {check.message}")


def print_robot_health(
    health: RobotHealth,
) -> None:
    print()
    print("Robot health")
    print("------------")
    print("Overall: " + ("OK" if health.ok else "FAILED"))

    for check in health.checks:
        print_health_check(check)

    if health.messages:
        print()
        print("Health messages")

        for message in health.messages:
            print(f"- {message}")


def main() -> int:
    print("Betabox Car status and health demo")
    print("==================================")

    try:
        with BetaboxCar() as car:
            print()
            print("Robot started")
            print("Capabilities: " + ", ".join(car.capability_names()))

            print_mapping(
                "Drive status",
                car.drive_status().to_dict(),
            )

            print_mapping(
                "Camera mount status",
                car.camera_mount_status().to_dict(),
            )

            print_mapping(
                "Sensors status",
                car.sensors_status().to_dict(),
            )

            print_mapping(
                "Audio status",
                car.audio_status().to_dict(),
            )

            print_mapping(
                "System status",
                car.system_status().to_dict(),
            )

            print_robot_health(car.health())

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
        logger.exception("Unexpected failure in status and health demo.")
        print()
        print(f"Unable to read robot status: {exc}")
        return 1

    print()
    print("Demo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
