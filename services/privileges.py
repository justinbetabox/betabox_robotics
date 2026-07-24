from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import NoReturn


BETABOX_EXECUTABLE = Path(
    "/opt/betabox/venv/bin/betabox"
)

SUDO_EXECUTABLE = Path(
    "/usr/bin/sudo"
)


def running_as_root() -> bool:
    """Return whether the current process has root privileges."""

    return os.geteuid() == 0


def elevate_betabox(
    arguments: list[str],
) -> NoReturn:
    """
    Re-execute an approved Betabox command as root.

    The installer must authorize the exact command through sudoers.
    ``sudo -n`` prevents interactive password prompts.
    """

    if not BETABOX_EXECUTABLE.is_file():
        raise RuntimeError(
            "Betabox executable is missing: "
            f"{BETABOX_EXECUTABLE}"
        )

    if not SUDO_EXECUTABLE.is_file():
        raise RuntimeError(
            "sudo is not installed."
        )

    command = [
        str(SUDO_EXECUTABLE),
        "-n",
        str(BETABOX_EXECUTABLE),
        *arguments,
    ]

    try:
        os.execv(
            str(SUDO_EXECUTABLE),
            command,
        )
    except OSError as exc:
        raise RuntimeError(
            f"Unable to elevate Betabox command: {exc}"
        ) from exc


def require_root_or_elevate(
    arguments: list[str],
) -> None:
    """
    Continue as root or transparently re-execute through sudo.
    """

    if running_as_root():
        return

    elevate_betabox(
        arguments
    )
