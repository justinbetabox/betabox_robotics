from __future__ import annotations

import importlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

from betabox_robotics.services.hardware_status import (
    RobotHardwareStatus,
    collect_hardware_status,
)
from betabox_robotics.services.http_health import (
    check_json_health,
)

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    message: str = ""


def run(command: list[str], timeout: int = 5) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception:
        return None


def check_imports(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> list[CheckResult]:
    checks: list[CheckResult] = []

    for module in config.verification.required_python_modules:
        try:
            imported = importlib.import_module(module)
            version = getattr(
                imported,
                "__version__",
                "",
            )

            checks.append(
                CheckResult(
                    f"import:{module}",
                    True,
                    version or "import ok",
                )
            )
        except Exception as exc:
            checks.append(
                CheckResult(
                    f"import:{module}",
                    False,
                    str(exc),
                )
            )

    return checks


def check_picamera2() -> CheckResult:
    try:
        importlib.import_module("picamera2")
        return CheckResult("camera:picamera2", True, "import ok")
    except Exception as exc:
        return CheckResult("camera:picamera2", False, str(exc))


def check_i2c_device(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> CheckResult:
    path = config.verification.i2c_device

    return CheckResult(
        "hardware:i2c",
        path.exists(),
        str(path) if path.exists() else f"{path} missing",
    )


def check_i2c_scan(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> CheckResult:
    bus = config.verification.i2c_bus

    result = run(
        ["i2cdetect", "-y", str(bus)],
        timeout=config.verification.command_timeout_seconds,
    )

    if result is None:
        return CheckResult("hardware:i2cdetect", False, "i2cdetect failed to run")

    if result.returncode != 0:
        return CheckResult(
            "hardware:i2cdetect",
            False,
            result.stderr.strip() or result.stdout.strip(),
        )

    output = result.stdout
    found = any(
        token not in ("--", "UU")
        and len(token) == 2
        and all(char in "0123456789abcdefABCDEF" for char in token)
        for token in output.split()
    )

    return CheckResult(
        "hardware:i2cdetect",
        found,
        "I2C devices found" if found else "no I2C devices found",
    )


def check_hifiberry(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> CheckResult:
    result = run(
        ["aplay", "-l"],
        timeout=config.verification.command_timeout_seconds,
    )

    if result is None:
        return CheckResult(
            "audio:hifiberry",
            False,
            "aplay failed to run",
        )

    output = result.stdout + result.stderr

    ok = any(
        identifier in output
        for identifier in (
            config.verification.hifiberry_identifiers
        )
    )

    return CheckResult(
        "audio:hifiberry",
        ok,
        (
            "HifiBerry detected"
            if ok
            else "HifiBerry not found in aplay -l"
        ),
    )


def check_speech_backend() -> CheckResult:
    try:
        from betabox_robotics.audio.speech import available_backends

        backends = available_backends()
        return CheckResult(
            "audio:speech_backend",
            bool(backends),
            ", ".join(backends) if backends else "no speech backends found",
        )
    except Exception as exc:
        return CheckResult("audio:speech_backend", False, str(exc))


def check_media_paths(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> list[CheckResult]:
    paths = (
        config.paths.pictures_dir,
        config.paths.videos_dir,
        config.paths.sounds_dir,
    )

    return [
        CheckResult(
            f"media:{path.name}",
            path.exists(),
            (
                str(path)
                if path.exists()
                else f"missing {path}"
            ),
        )
        for path in paths
    ]


def check_robot_constructs() -> CheckResult:
    car = None

    try:
        from betabox_robotics import BetaboxCar

        car = BetaboxCar()

        return CheckResult(
            "robot:construct",
            True,
            "BetaboxCar constructed successfully",
        )

    except Exception as exc:
        return CheckResult(
            "robot:construct",
            False,
            str(exc),
        )

    finally:
        if car is not None:
            try:
                car.close()
            except Exception:
                pass


def check_configurable_http_proxy() -> CheckResult:
    result = run(["configurable-http-proxy", "--version"])

    if result is None or result.returncode != 0:
        return CheckResult(
            "jupyterhub:proxy",
            False,
            "configurable-http-proxy not installed",
        )

    output = result.stdout.strip() or result.stderr.strip()

    return CheckResult(
        "jupyterhub:proxy",
        True,
        output or "installed",
    )


def check_launchpad(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> CheckResult:
    service_result = run(
        [
            "systemctl",
            "is-active",
            config.services.launchpad,
        ],
        timeout=(
            config.verification.command_timeout_seconds
        ),
    )

    if (
        service_result is None
        or service_result.returncode != 0
    ):
        state = (
            service_result.stdout.strip()
            if service_result is not None
            else "unknown"
        )

        return CheckResult(
            "launchpad:http",
            False,
            (
                f"{config.services.launchpad} "
                f"is {state or 'not active'}"
            ),
        )

    ok, message = check_json_health(
        config.network.launchpad_health_url,
        expected_service="launchpad",
        timeout=(
            config.verification.command_timeout_seconds
        ),
    )

    return CheckResult(
        "launchpad:http",
        ok,
        (
            "Launchpad responding"
            if ok
            else message
        ),
    )

def checks_from_hardware_status(
    hardware: RobotHardwareStatus,
) -> list[CheckResult]:
    checks: list[CheckResult] = []

    checks.append(
        CheckResult(
            "hardware:i2c",
            hardware.i2c.available,
            (
                ", ".join(hardware.i2c.devices)
                if hardware.i2c.devices
                else hardware.i2c.error or "no I²C devices detected"
            ),
        )
    )

    checks.append(
        CheckResult(
            "hardware:robot",
            hardware.robot_available,
            hardware.robot_error or "robot hardware available",
        )
    )

    battery = hardware.battery

    checks.append(
        CheckResult(
            "hardware:battery",
            battery.available and battery.state != "critical",
            (
                f"{battery.voltage:.2f} V — {battery.state}"
                if battery.available and battery.voltage is not None
                else battery.error or "battery unavailable"
            ),
        )
    )

    sensors = hardware.sensors

    checks.append(
        CheckResult(
            "hardware:grayscale",
            sensors.grayscale_available,
            (
                ", ".join(
                    str(value)
                    for value in sensors.grayscale_values or []
                )
                if sensors.grayscale_available
                else sensors.error or "grayscale unavailable"
            ),
        )
    )

    checks.append(
        CheckResult(
            "hardware:ultrasonic_configured",
            sensors.ultrasonic_configured,
            (
                "ultrasonic configured"
                if sensors.ultrasonic_configured
                else "ultrasonic not configured"
            ),
        )
    )

    checks.append(
        CheckResult(
            "audio:hifiberry",
            hardware.audio.available,
            hardware.audio.device
            or hardware.audio.error
            or "audio unavailable",
        )
    )

    vision = hardware.vision

    vision_ok = (
        vision.service_available
        and vision.running
        and vision.camera_running
        and vision.camera_has_frame
    )

    checks.append(
        CheckResult(
            "vision:service",
            vision_ok,
            (
                "Vision service and camera pipeline healthy"
                if vision_ok
                else vision.error or "Vision service degraded"
            ),
        )
    )

    return checks


def check_ultrasonic_read() -> CheckResult:
    try:
        from betabox_robotics.robots.betabox_car import BETABOX_CAR
        from betabox_robotics.sensors import Sensors

        sensors = Sensors.default(
            BETABOX_CAR.sensors
        )

        try:
            distance = float(sensors.ultrasonic.distance(samples=3))
        finally:
            close = getattr(sensors, "close", None)

            if callable(close):
                close()

        if distance < 0:
            return CheckResult(
                "hardware:ultrasonic_read",
                False,
                f"invalid distance result: {distance}",
            )

        return CheckResult(
            "hardware:ultrasonic_read",
            True,
            f"{distance:.1f} cm",
        )

    except Exception as exc:
        return CheckResult(
            "hardware:ultrasonic_read",
            False,
            str(exc),
        )


def collect_checks(
    *,
    include_robot: bool = True,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> list[CheckResult]:
    checks: list[CheckResult] = []

    checks.extend(check_imports(config))
    checks.append(check_picamera2())
    checks.append(
        check_configurable_http_proxy()
    )
    checks.append(
        check_launchpad(config)
    )
    checks.append(
        check_speech_backend()
    )
    checks.extend(
        check_media_paths(config)
    )

    hardware = collect_hardware_status(
        config
    )

    checks.extend(
        checks_from_hardware_status(
            hardware
        )
    )

    if include_robot:
        checks.append(
            check_robot_constructs()
        )

    return checks


def print_results(checks: list[CheckResult]) -> bool:
    print()
    print("Betabox Verification")
    print("====================")
    print()

    all_ok = True

    for check in checks:
        status = "OK" if check.ok else "FAIL"
        print(f"[{status}] {check.name}")

        if check.message:
            print(f"     {check.message}")

        if not check.ok:
            all_ok = False

    print()

    if all_ok:
        print("Betabox verification passed.")
    else:
        print("Betabox verification failed.")

    return all_ok


def main() -> int:
    config = DEFAULT_PLATFORM_CONFIG

    checks = collect_checks(config=config)
    return 0 if print_results(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
