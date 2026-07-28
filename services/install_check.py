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

AVAHI_OVERRIDE_PATH = Path("/etc/systemd/system/avahi-daemon.service.d/override.conf")

AVAHI_OVERRIDE_REQUIRED_LINES = (
    "After=set-hostname-from-serial.service",
    "After=NetworkManager.service",
    "After=NetworkManager-wait-online.service",
    "Wants=set-hostname-from-serial.service",
    "Wants=NetworkManager-wait-online.service",
)


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


def check_avahi_override(
    path: Path = AVAHI_OVERRIDE_PATH,
) -> CheckResult:
    """Verify the Avahi systemd startup-ordering override."""

    if not path.is_file():
        return CheckResult(
            "systemd-override:avahi-daemon",
            False,
            f"{path} missing",
        )

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError as exc:
        return CheckResult(
            "systemd-override:avahi-daemon",
            False,
            str(exc),
        )

    missing_lines = [line for line in AVAHI_OVERRIDE_REQUIRED_LINES if line not in text]

    if missing_lines:
        return CheckResult(
            "systemd-override:avahi-daemon",
            False,
            "missing: " + ", ".join(missing_lines),
        )

    return CheckResult(
        "systemd-override:avahi-daemon",
        True,
        str(path),
    )


def check_media_root(
    name: str,
    media_root: Path,
    *,
    success_message: str | None = None,
) -> CheckResult:
    """Verify that a Betabox media directory contains all required paths."""

    required_paths = (
        media_root / "pictures",
        media_root / "videos",
        media_root / "sounds",
        media_root / "sounds" / "car-honk.mp3",
    )

    problems: list[str] = []

    for path in required_paths:
        try:
            if not path.exists():
                problems.append(f"{path}: missing")
        except PermissionError:
            problems.append(f"{path}: permission denied")
        except OSError as exc:
            problems.append(f"{path}: {exc}")

    if problems:
        return CheckResult(
            name,
            False,
            "; ".join(problems),
        )

    return CheckResult(
        name,
        True,
        success_message or str(media_root),
    )


def check_runtime_media(
    username: str,
) -> CheckResult:
    """Verify the runtime media tree for the Betabox service account."""

    try:
        user = pwd.getpwnam(username)
    except KeyError:
        return CheckResult(
            f"runtime-media:{username}",
            False,
            "service user does not exist",
        )

    media_root = Path(user.pw_dir) / "media"

    return check_media_root(
        f"runtime-media:{username}",
        media_root,
    )


def check_account_workspace(
    username: str,
    home: Path,
) -> CheckResult:
    """Verify the media tree within a managed account workspace."""

    return check_media_root(
        f"workspace:{username}",
        home / "media",
        success_message=str(home),
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

    checks.append(check_avahi_override())

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


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
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

    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
) -> int:
    args = parse_args(argv)
    config = DEFAULT_PLATFORM_CONFIG

    service_user = resolve_service_user(args.service_user)

    checks = collect_checks(
        config,
        service_user=service_user,
    )

    return 0 if print_results(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
