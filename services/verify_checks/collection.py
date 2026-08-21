from __future__ import annotations

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
from betabox_robotics.services.hardware_status import (
    collect_hardware_status,
)

from .hardware import (
    check_robot_constructs,
    checks_from_hardware_status,
)
from .launchpad import check_launchpad
from .media import check_media_paths
from .models import CheckResult
from .software import (
    check_configurable_http_proxy,
    check_import,
    check_picamera2,
    check_speech_backend,
)
from .validation import (
    validate_config,
    validate_include_robot,
)


def _validate_robot_config(
    value: object,
) -> RobotConfig:
    if not isinstance(
        value,
        RobotConfig,
    ):
        raise TypeError("robot_config must be a RobotConfig")

    return value


def collect_checks(
    *,
    include_robot: bool = True,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
    robot_config: RobotConfig = BETABOX_CAR,
) -> tuple[CheckResult, ...]:
    config_value = validate_config(config)
    include_robot_value = validate_include_robot(include_robot)
    robot_config_value = _validate_robot_config(robot_config)

    verification = config_value.verification
    checks: list[CheckResult] = []

    for module in verification.required_python_modules:
        checks.append(check_import(module))

    checks.append(check_picamera2())
    checks.append(
        check_configurable_http_proxy(timeout=(verification.command_timeout_seconds))
    )
    checks.append(check_launchpad(config_value))
    checks.append(check_speech_backend())
    checks.extend(check_media_paths(config_value))

    hardware = collect_hardware_status(
        config_value,
        robot_config=robot_config_value,
    )

    checks.extend(checks_from_hardware_status(hardware))

    if include_robot_value:
        checks.append(
            check_robot_constructs(
                robot_config=robot_config_value,
            )
        )

    return tuple(checks)
