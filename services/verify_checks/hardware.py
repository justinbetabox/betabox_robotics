from __future__ import annotations

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.hardware.exceptions import (
    HardwareError,
)
from betabox_robotics.robots.betabox_car import (
    BETABOX_CAR,
)
from betabox_robotics.robots.config import (
    RobotConfig,
)
from betabox_robotics.robots.exceptions import (
    RobotError,
)
from betabox_robotics.sensors.exceptions import (
    SensorError,
)
from betabox_robotics.services.command import run
from betabox_robotics.services.hardware_checks import (
    RobotHardwareStatus,
)

from .models import CheckResult
from .validation import (
    validate_config,
    validate_hardware_status,
    validate_timeout,
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


def check_i2c_device(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> CheckResult:
    """
    Verify that the configured I2C device exists.
    """

    config_value = validate_config(config)
    path = config_value.verification.i2c_device

    try:
        exists = path.exists()
    except OSError as exc:
        return CheckResult(
            name="hardware:i2c",
            ok=False,
            message=str(exc),
        )

    return CheckResult(
        name="hardware:i2c",
        ok=exists,
        message=(str(path) if exists else f"{path} missing"),
    )


def check_i2c_scan(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> CheckResult:
    """
    Run i2cdetect and verify that at least one device
    address is present.
    """

    config_value = validate_config(config)
    verification = config_value.verification
    timeout_value = validate_timeout(verification.command_timeout_seconds)
    bus = verification.i2c_bus

    result = run(
        [
            "i2cdetect",
            "-y",
            str(bus),
        ],
        timeout=timeout_value,
    )

    if result is None:
        return CheckResult(
            name="hardware:i2cdetect",
            ok=False,
            message="i2cdetect failed to run",
        )

    if result.returncode != 0:
        return CheckResult(
            name="hardware:i2cdetect",
            ok=False,
            message=(
                result.stderr.strip() or result.stdout.strip() or "i2cdetect failed"
            ),
        )

    found = any(
        token
        not in {
            "--",
            "UU",
        }
        and len(token) == 2
        and all(character in "0123456789abcdefABCDEF" for character in token)
        for token in result.stdout.split()
    )

    return CheckResult(
        name="hardware:i2cdetect",
        ok=found,
        message=("I2C devices found" if found else "no I2C devices found"),
    )


def check_hifiberry(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> CheckResult:
    """
    Verify that a configured HifiBerry identifier is
    present in the ALSA device listing.
    """

    config_value = validate_config(config)
    verification = config_value.verification
    timeout_value = validate_timeout(verification.command_timeout_seconds)

    result = run(
        [
            "aplay",
            "-l",
        ],
        timeout=timeout_value,
    )

    if result is None:
        return CheckResult(
            name="audio:hifiberry",
            ok=False,
            message="aplay failed to run",
        )

    if result.returncode != 0:
        return CheckResult(
            name="audio:hifiberry",
            ok=False,
            message=(result.stderr.strip() or result.stdout.strip() or "aplay failed"),
        )

    output = result.stdout + result.stderr

    detected = any(
        identifier in output for identifier in (verification.hifiberry_identifiers)
    )

    return CheckResult(
        name="audio:hifiberry",
        ok=detected,
        message=(
            "HifiBerry detected" if detected else ("HifiBerry not found in aplay -l")
        ),
    )


def check_robot_constructs(
    *,
    robot_config: RobotConfig = BETABOX_CAR,
) -> CheckResult:
    """
    Verify that a BetaboxCar can be constructed and
    closed using the selected robot configuration.
    """

    robot_config_value = _validate_robot_config(robot_config)

    try:
        from betabox_robotics import BetaboxCar

        car = BetaboxCar(robot_config_value)

    except (
        HardwareError,
        RobotError,
        OSError,
    ) as exc:
        return CheckResult(
            name="robot:construct",
            ok=False,
            message=str(exc),
        )

    try:
        car.close()
    except (
        HardwareError,
        RobotError,
        OSError,
    ) as exc:
        return CheckResult(
            name="robot:construct",
            ok=False,
            message=(f"BetaboxCar constructed but could not close: {exc}"),
        )

    return CheckResult(
        name="robot:construct",
        ok=True,
        message=("BetaboxCar constructed successfully"),
    )


def checks_from_hardware_status(
    hardware: RobotHardwareStatus,
) -> tuple[CheckResult, ...]:
    """
    Convert a collected RobotHardwareStatus into
    verification check results.
    """

    hardware_value = validate_hardware_status(hardware)

    i2c = hardware_value.i2c

    i2c_message = (
        ", ".join(i2c.devices)
        if i2c.devices
        else (i2c.error or "no I2C devices detected")
    )

    passive_message = (
        hardware_value.passive_hardware_error or "robot hardware available"
    )

    battery = hardware_value.battery

    battery_ok = battery.available and battery.state != "critical"

    battery_message = (
        f"{battery.voltage:.2f} V — {battery.state}"
        if (battery.available and battery.voltage is not None)
        else (battery.error or "battery unavailable")
    )

    sensors = hardware_value.sensors

    grayscale_message = (
        ", ".join(str(value) for value in (sensors.grayscale_values or ()))
        if sensors.grayscale_available
        else (sensors.error or "grayscale unavailable")
    )

    ultrasonic_message = (
        "ultrasonic configured"
        if sensors.ultrasonic_configured
        else "ultrasonic not configured"
    )

    audio = hardware_value.audio

    audio_message = audio.device or audio.error or "audio unavailable"

    vision = hardware_value.vision

    vision_ok = (
        vision.service_available
        and vision.running
        and vision.camera_running
        and vision.camera_has_frame
    )

    vision_message = (
        ("Vision service and camera pipeline healthy")
        if vision_ok
        else (vision.error or "Vision service degraded")
    )

    return (
        CheckResult(
            name="hardware:i2c",
            ok=i2c.available,
            message=i2c_message,
        ),
        CheckResult(
            name="hardware:robot",
            ok=(hardware_value.passive_hardware_available),
            message=passive_message,
        ),
        CheckResult(
            name="hardware:battery",
            ok=battery_ok,
            message=battery_message,
        ),
        CheckResult(
            name="hardware:grayscale",
            ok=sensors.grayscale_available,
            message=grayscale_message,
        ),
        CheckResult(
            name=("hardware:ultrasonic_configured"),
            ok=sensors.ultrasonic_configured,
            message=ultrasonic_message,
        ),
        CheckResult(
            name="audio:hifiberry",
            ok=audio.available,
            message=audio_message,
        ),
        CheckResult(
            name="vision:service",
            ok=vision_ok,
            message=vision_message,
        ),
    )


def check_ultrasonic_read(
    *,
    robot_config: RobotConfig = BETABOX_CAR,
) -> CheckResult:
    """
    Construct the Sensors subsystem and perform one
    sampled ultrasonic distance read.
    """

    robot_config_value = _validate_robot_config(robot_config)

    try:
        from betabox_robotics.sensors import Sensors

        sensors = Sensors.default(robot_config_value.sensors)

    except (
        HardwareError,
        SensorError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        return CheckResult(
            name="hardware:ultrasonic_read",
            ok=False,
            message=str(exc),
        )

    try:
        distance = float(sensors.ultrasonic.distance(samples=3))

    except (
        HardwareError,
        SensorError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        return CheckResult(
            name="hardware:ultrasonic_read",
            ok=False,
            message=str(exc),
        )

    finally:
        try:
            sensors.close()
        except (
            HardwareError,
            SensorError,
            OSError,
        ) as exc:
            return CheckResult(
                name="hardware:ultrasonic_read",
                ok=False,
                message=(f"ultrasonic read succeeded but cleanup failed: {exc}"),
            )

    if distance < 0:
        return CheckResult(
            name="hardware:ultrasonic_read",
            ok=False,
            message=f"invalid distance result: {distance}",
        )

    return CheckResult(
        name="hardware:ultrasonic_read",
        ok=True,
        message=f"{distance:.1f} cm",
    )
