from __future__ import annotations

import argparse
import importlib
import os
import pwd
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.accounts import BETABOX_ACCOUNTS


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    message: str = ""


def run(
    command: list[str],
    timeout: int = 5,
) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception:
        return None


def resolve_service_user(
    requested_user: str | None = None,
) -> str:
    if requested_user:
        return requested_user

    sudo_user = os.environ.get("SUDO_USER")

    if sudo_user:
        return sudo_user

    return pwd.getpwuid(os.getuid()).pw_name


def check_import(module: str) -> CheckResult:
    try:
        imported = importlib.import_module(module)
        version = getattr(imported, "__version__", "")
        return CheckResult(f"import:{module}", True, version or "import ok")
    except Exception as exc:
        return CheckResult(f"import:{module}", False, str(exc))


def check_command(
    command: list[str],
    name: str,
    *,
    timeout: int = 5,
) -> CheckResult:
    result = run(
        command,
        timeout=timeout,
    )

    if result is None:
        return CheckResult(
            name,
            False,
            "command failed to run",
        )

    return CheckResult(
        name,
        result.returncode == 0,
        (result.stdout.strip() or result.stderr.strip()),
    )


def check_config_line(
    line: str,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> CheckResult:
    config_file = config.verification.boot_config_file

    if not config_file.exists():
        return CheckResult(
            f"config:{line}",
            False,
            f"{config_file} missing",
        )

    try:
        text = config_file.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except Exception as exc:
        return CheckResult(
            f"config:{line}",
            False,
            str(exc),
        )

    present = line in text

    return CheckResult(
        f"config:{line}",
        present,
        "present" if present else "missing",
    )


def check_runtime_media(
    username: str,
) -> CheckResult:
    try:
        user = pwd.getpwnam(username)
    except KeyError:
        return CheckResult(
            f"runtime-media:{username}",
            False,
            "service user does not exist",
        )

    home = Path(user.pw_dir)
    media_root = home / "media"

    required_paths = (
        media_root / "pictures",
        media_root / "videos",
        media_root / "sounds",
        media_root / "sounds" / "car-honk.mp3",
    )

    problems: list[str] = []

    for path in required_paths:
        try:
            exists = path.exists()
        except PermissionError:
            problems.append(f"{path}: permission denied")
            continue
        except OSError as exc:
            problems.append(f"{path}: {exc}")
            continue

        if not exists:
            problems.append(f"{path}: missing")

    if problems:
        return CheckResult(
            f"runtime-media:{username}",
            False,
            "; ".join(problems),
        )

    return CheckResult(
        f"runtime-media:{username}",
        True,
        str(media_root),
    )


def check_executable(command: str) -> CheckResult:
    path = shutil.which(command)

    return CheckResult(
        f"command:{command}",
        path is not None,
        path if path else "not found",
    )


def check_service_installed(
    unit: str,
) -> CheckResult:
    path = Path("/etc/systemd/system") / unit

    return CheckResult(
        f"service-installed:{unit}",
        path.is_file(),
        "installed" if path.is_file() else "unit file missing",
    )


def check_service_enabled(
    unit: str,
    *,
    timeout: int = 5,
) -> CheckResult:
    result = run(
        [
            "systemctl",
            "is-enabled",
            unit,
        ],
        timeout=timeout,
    )

    if result is None:
        return CheckResult(
            f"service-enabled:{unit}",
            False,
            "systemctl command failed",
        )

    output = result.stdout.strip() or result.stderr.strip() or "unknown"

    return CheckResult(
        f"service-enabled:{unit}",
        result.returncode == 0,
        output,
    )


def check_account_workspace(
    username: str,
    home: Path,
) -> CheckResult:
    media_root = home / "media"

    required_paths = (
        media_root / "pictures",
        media_root / "videos",
        media_root / "sounds",
        media_root / "sounds" / "car-honk.mp3",
    )

    problems: list[str] = []

    for path in required_paths:
        try:
            exists = path.exists()
        except PermissionError:
            problems.append(f"{path}: permission denied")
            continue
        except OSError as exc:
            problems.append(f"{path}: {exc}")
            continue

        if not exists:
            problems.append(f"{path}: missing")

    if problems:
        return CheckResult(
            f"workspace:{username}",
            False,
            "; ".join(problems),
        )

    return CheckResult(
        f"workspace:{username}",
        True,
        str(home),
    )


def collect_checks(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
    *,
    service_user: str,
) -> list[CheckResult]:
    betabox_command = str(Path(sys.executable).parent / "betabox")

    checks: list[CheckResult] = []
    verification = config.verification

    for module in verification.required_python_modules:
        checks.append(check_import(module))

    checks.append(
        check_command(
            [betabox_command, "--help"],
            "cli:betabox",
            timeout=verification.command_timeout_seconds,
        )
    )

    checks.append(
        check_command(
            [
                betabox_command,
                "launchpad",
                "--help",
            ],
            "cli:betabox-launchpad",
            timeout=verification.command_timeout_seconds,
        )
    )

    for line in verification.required_boot_config_lines:
        checks.append(
            check_config_line(
                line,
                config,
            )
        )

    for account in BETABOX_ACCOUNTS:
        checks.append(
            check_account_workspace(
                account.username,
                account.home,
            )
        )

    checks.append(check_runtime_media(service_user))

    for executable in verification.required_executables:
        checks.append(check_executable(executable))

    for unit in config.services.all_units:
        checks.append(check_service_installed(unit))

        checks.append(
            check_service_enabled(
                unit,
                timeout=(verification.command_timeout_seconds),
            )
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify the Betabox software installation.",
    )

    parser.add_argument(
        "--service-user",
        help=(
            "Linux account used by Betabox services. "
            "Defaults to SUDO_USER when run through sudo."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = DEFAULT_PLATFORM_CONFIG

    service_user = resolve_service_user(args.service_user)

    checks = collect_checks(
        config,
        service_user=service_user,
    )

    return 0 if print_results(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
