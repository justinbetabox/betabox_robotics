from __future__ import annotations

import json

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.robots.config import (
    RobotConfig,
)
from betabox_robotics.robots.defaults import (
    BETABOX_CAR,
)
from betabox_robotics.services.hardware_checks import (
    RobotHardwareStatus,
    collect_audio_status,
    collect_i2c_status,
    collect_robot_status,
    collect_vision_status,
)


def _validate_config(
    value: object,
) -> PlatformConfig:
    if not isinstance(
        value,
        PlatformConfig,
    ):
        raise TypeError("config must be a PlatformConfig")

    return value


def _validate_robot_config(
    value: object,
) -> RobotConfig:
    if not isinstance(
        value,
        RobotConfig,
    ):
        raise TypeError("robot_config must be a RobotConfig")

    return value


def collect_hardware_status(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
    *,
    robot_config: RobotConfig = BETABOX_CAR,
) -> RobotHardwareStatus:
    config_value = _validate_config(config)
    robot_config_value = _validate_robot_config(robot_config)

    i2c = collect_i2c_status(config_value)
    audio = collect_audio_status(config_value)
    vision = collect_vision_status(config_value)

    (
        passive_hardware_available,
        battery,
        sensors,
        passive_hardware_error,
    ) = collect_robot_status(robot_config_value.sensors)

    return RobotHardwareStatus(
        i2c=i2c,
        passive_hardware_available=passive_hardware_available,
        battery=battery,
        sensors=sensors,
        audio=audio,
        vision=vision,
        passive_hardware_error=passive_hardware_error,
    )


def main() -> int:
    status = collect_hardware_status(DEFAULT_PLATFORM_CONFIG)

    print(
        json.dumps(
            status.to_dict(),
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
