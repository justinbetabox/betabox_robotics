from __future__ import annotations

import stat
from pathlib import Path

from betabox_robotics.services.command import run

from .models import CheckResult
from .validation import validate_string

CLOCK_HELPER_PATH = Path("/usr/local/libexec/betabox-clock-set")
CLOCK_SUDOERS_PATH = Path("/etc/sudoers.d/betabox-clock")


def check_clock_helper(
    path: Path = CLOCK_HELPER_PATH,
) -> CheckResult:
    """
    Verify the protected clock helper is installed securely.
    """

    name = "clock:helper"

    try:
        info = path.lstat()
    except OSError as exc:
        return CheckResult(
            name=name,
            ok=False,
            message=str(exc),
        )

    if not stat.S_ISREG(info.st_mode):
        return CheckResult(
            name=name,
            ok=False,
            message="helper is not a regular file",
        )

    if info.st_uid != 0 or info.st_gid != 0:
        return CheckResult(
            name=name,
            ok=False,
            message="helper must be owned by root:root",
        )

    if stat.S_IMODE(info.st_mode) != 0o755:
        return CheckResult(
            name=name,
            ok=False,
            message="helper must have permissions 0755",
        )

    return CheckResult(
        name=name,
        ok=True,
        message=f"{path} (root:root, 0755)",
    )


def check_clock_sudoers(
    service_user: str,
    path: Path = CLOCK_SUDOERS_PATH,
) -> CheckResult:
    """
    Verify the clock helper's privilege policy.
    """

    user = validate_string(
        service_user,
        name="service_user",
    )

    name = "clock:sudoers"

    try:
        info = path.lstat()
        contents = path.read_text(encoding="utf-8")
    except OSError as exc:
        return CheckResult(
            name=name,
            ok=False,
            message=str(exc),
        )

    if not stat.S_ISREG(info.st_mode):
        return CheckResult(
            name=name,
            ok=False,
            message="sudoers policy is not a regular file",
        )

    if info.st_uid != 0 or info.st_gid != 0:
        return CheckResult(
            name=name,
            ok=False,
            message="sudoers policy must be owned by root:root",
        )

    if stat.S_IMODE(info.st_mode) != 0o440:
        return CheckResult(
            name=name,
            ok=False,
            message="sudoers policy must have permissions 0440",
        )

    expected_rule = (
        f"{user} ALL=(root) NOPASSWD: "
        "/usr/local/libexec/betabox-clock-set "
        "^[0-9]{13}$"
    )

    if expected_rule not in contents.splitlines():
        return CheckResult(
            name=name,
            ok=False,
            message="expected clock helper rule missing",
        )

    result = run(
        ["/usr/sbin/visudo", "-cf", str(path)],
        timeout=5,
    )

    if result is None or result.returncode != 0:
        return CheckResult(
            name=name,
            ok=False,
            message="sudoers policy validation failed",
        )

    return CheckResult(
        name=name,
        ok=True,
        message=f"{path} (root:root, 0440, valid)",
    )
