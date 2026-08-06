from __future__ import annotations

from pathlib import Path

from betabox_robotics.services.command import run

from .models import CheckResult
from .validation import (
    validate_path,
    validate_string,
    validate_timeout,
)

AVAHI_OVERRIDE_PATH = Path("/etc/systemd/system/avahi-daemon.service.d/override.conf")

AVAHI_OVERRIDE_REQUIRED_LINES = (
    "After=set-hostname-from-serial.service",
    "After=NetworkManager.service",
    "After=NetworkManager-wait-online.service",
    "Wants=set-hostname-from-serial.service",
    "Wants=NetworkManager-wait-online.service",
)


def check_service_installed(
    unit: str,
    *,
    systemd_root: str | Path = ("/etc/systemd/system"),
) -> CheckResult:
    """
    Verify that a systemd unit file is installed.
    """

    unit_value = validate_string(
        unit,
        name="unit",
    )
    systemd_root_value = validate_path(
        systemd_root,
        name="systemd_root",
    )
    path = systemd_root_value / unit_value

    try:
        installed = path.is_file()
    except OSError as exc:
        return CheckResult(
            name=(f"service-installed:{unit_value}"),
            ok=False,
            message=str(exc),
        )

    return CheckResult(
        name=(f"service-installed:{unit_value}"),
        ok=installed,
        message=("installed" if installed else "unit file missing"),
    )


def check_service_enabled(
    unit: str,
    *,
    timeout: int = 5,
) -> CheckResult:
    """
    Verify that a systemd service is enabled.
    """

    unit_value = validate_string(
        unit,
        name="unit",
    )
    timeout_value = validate_timeout(timeout)

    result = run(
        [
            "systemctl",
            "is-enabled",
            unit_value,
        ],
        timeout=timeout_value,
    )

    if result is None:
        return CheckResult(
            name=(f"service-enabled:{unit_value}"),
            ok=False,
            message=("systemctl command failed"),
        )

    output = result.stdout.strip() or result.stderr.strip() or "unknown"

    return CheckResult(
        name=(f"service-enabled:{unit_value}"),
        ok=result.returncode == 0,
        message=output,
    )


def check_avahi_override(
    path: str | Path = AVAHI_OVERRIDE_PATH,
) -> CheckResult:
    """
    Verify the Avahi systemd startup-ordering override.
    """

    path_value = validate_path(
        path,
        name="path",
    )
    check_name = "systemd-override:avahi-daemon"

    try:
        exists = path_value.is_file()
    except OSError as exc:
        return CheckResult(
            name=check_name,
            ok=False,
            message=str(exc),
        )

    if not exists:
        return CheckResult(
            name=check_name,
            ok=False,
            message=f"{path_value} missing",
        )

    try:
        text = path_value.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError as exc:
        return CheckResult(
            name=check_name,
            ok=False,
            message=str(exc),
        )

    missing_lines = tuple(
        line for line in (AVAHI_OVERRIDE_REQUIRED_LINES) if line not in text
    )

    if missing_lines:
        return CheckResult(
            name=check_name,
            ok=False,
            message=("missing: " + ", ".join(missing_lines)),
        )

    return CheckResult(
        name=check_name,
        ok=True,
        message=str(path_value),
    )
