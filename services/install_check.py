from __future__ import annotations

import importlib
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

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


def check_import(module: str) -> CheckResult:
    try:
        imported = importlib.import_module(module)
        version = getattr(imported, "__version__", "")
        return CheckResult(f"import:{module}", True, version or "import ok")
    except Exception as exc:
        return CheckResult(f"import:{module}", False, str(exc))


def check_command(command: list[str], name: str) -> CheckResult:
    result = run(command)

    if result is None:
        return CheckResult(name, False, "command failed to run")

    return CheckResult(
        name,
        result.returncode == 0,
        result.stdout.strip() or result.stderr.strip(),
    )


def check_config_line(
    line: str,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> CheckResult:
    config_file = (
        config.verification.boot_config_file
    )

    if not config_file.exists():
        return CheckResult(
            f"config:{line}",
            False,
            f"{config_file} missing",
        )

    text = config_file.read_text(
        errors="ignore",
    )

    return CheckResult(
        f"config:{line}",
        line in text,
        "present" if line in text else "missing",
    )


def check_path(path: Path) -> CheckResult:
    return CheckResult(
        f"path:{path}",
        path.exists(),
        "exists" if path.exists() else "missing",
    )


def check_executable(command: str) -> CheckResult:
    path = shutil.which(command)

    return CheckResult(
        f"command:{command}",
        path is not None,
        path if path else "not found",
    )


def collect_checks(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> list[CheckResult]:
    checks: list[CheckResult] = []

    for module in (
        config.verification.required_python_modules
    ):
        checks.append(check_import(module))

    checks.append(
        check_command(
            ["betabox", "--help"],
            "cli:betabox",
        )
    )

    for line in (
        config.verification.required_boot_config_lines
    ):
        checks.append(
            check_config_line(
                line,
                config,
            )
        )

    for path in (
        config.paths.pictures_dir,
        config.paths.videos_dir,
        config.paths.sounds_dir,
        config.paths.car_honk_sound,
    ):
        checks.append(check_path(path))

    for executable in (
        config.verification.required_executables
    ):
        checks.append(
            check_executable(executable)
        )

    return checks


def print_results(checks: list[CheckResult]) -> bool:
    print()
    print("Betabox Install Check")
    print("=====================")
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
        print("Betabox installation check passed.")
        print()
        print("A reboot is required before hardware verification.")
        print()
        print("After reboot:")
        print("  source /opt/betabox/venv/bin/activate")
        print("  betabox verify")
        print("  betabox doctor")
    else:
        print("Betabox installation check failed.")

    return all_ok


def main() -> int:
    config = DEFAULT_PLATFORM_CONFIG
    checks = collect_checks(config)

    return (
        0
        if print_results(checks)
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
