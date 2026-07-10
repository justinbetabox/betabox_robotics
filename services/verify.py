from __future__ import annotations

import importlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

from betabox_robotics.services.hardware_status import (
    RobotHardwareStatus,
    collect_hardware_status,
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


def check_imports() -> list[CheckResult]:
    checks: list[CheckResult] = []

    modules = [
        "betabox_robotics",
        "cv2",
        "numpy",
        "pyaudio",
        "gpiozero",
        "smbus2",
        "aiohttp",
        "aiortc",
    ]

    for module in modules:
        try:
            imported = importlib.import_module(module)
            version = getattr(imported, "__version__", "")
            message = version if version else "import ok"
            checks.append(CheckResult(f"import:{module}", True, message))
        except Exception as exc:
            checks.append(CheckResult(f"import:{module}", False, str(exc)))

    return checks


def check_picamera2() -> CheckResult:
    try:
        importlib.import_module("picamera2")
        return CheckResult("camera:picamera2", True, "import ok")
    except Exception as exc:
        return CheckResult("camera:picamera2", False, str(exc))


def check_i2c_device() -> CheckResult:
    path = Path("/dev/i2c-1")
    return CheckResult(
        "hardware:i2c",
        path.exists(),
        str(path) if path.exists() else "/dev/i2c-1 missing",
    )


def check_i2c_scan() -> CheckResult:
    result = run(["i2cdetect", "-y", "1"], timeout=5)

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


def check_hifiberry() -> CheckResult:
    result = run(["aplay", "-l"], timeout=5)

    if result is None:
        return CheckResult("audio:hifiberry", False, "aplay failed to run")

    output = result.stdout + result.stderr
    ok = "snd_rpi_hifiberry_dac" in output or "HifiBerry" in output

    return CheckResult(
        "audio:hifiberry",
        ok,
        "HifiBerry detected" if ok else "HifiBerry not found in aplay -l",
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


def check_media_paths() -> list[CheckResult]:
    paths = [
        Path.home() / "media" / "pictures",
        Path.home() / "media" / "videos",
        Path.home() / "media" / "sounds",
    ]

    return [
        CheckResult(
            f"media:{path.name}",
            path.exists(),
            str(path) if path.exists() else f"missing {path}",
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
                car.drive.stop()
            except Exception:
                pass

            for subsystem in (
                car.audio,
                car.drive,
                car.sensors,
                car.system,
            ):
                close = getattr(subsystem, "close", None)

                if callable(close):
                    try:
                        close()
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

        sensors = Sensors.default(BETABOX_CAR)

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

def collect_checks(*, include_robot: bool = True) -> list[CheckResult]:
    checks: list[CheckResult] = []

    checks.extend(check_imports())
    checks.append(check_picamera2())
    checks.append(check_configurable_http_proxy())
    checks.append(check_speech_backend())
    checks.extend(check_media_paths())

    hardware = collect_hardware_status()
    checks.extend(checks_from_hardware_status(hardware))

    if include_robot:
        checks.append(check_robot_constructs())
        checks.append(check_ultrasonic_read())

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
    checks = collect_checks()
    return 0 if print_results(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
