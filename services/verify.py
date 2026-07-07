from __future__ import annotations

import importlib
import subprocess
from dataclasses import dataclass
from pathlib import Path


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
    try:
        from betabox_robotics import BetaboxCar

        car = BetaboxCar()
        car.close()
        return CheckResult("robot:construct", True, "BetaboxCar constructed and closed")
    except Exception as exc:
        return CheckResult("robot:construct", False, str(exc))


def collect_checks(*, include_robot: bool = True) -> list[CheckResult]:
    checks: list[CheckResult] = []

    checks.extend(check_imports())
    checks.append(check_picamera2())
    checks.append(check_i2c_device())
    checks.append(check_i2c_scan())
    checks.append(check_hifiberry())
    checks.append(check_speech_backend())
    checks.extend(check_media_paths())

    if include_robot:
        checks.append(check_robot_constructs())

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
