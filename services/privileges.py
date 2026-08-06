from __future__ import annotations

import os
from pathlib import Path
from typing import NoReturn

BETABOX_EXECUTABLE = Path("/opt/betabox/venv/bin/betabox")

SUDO_EXECUTABLE = Path("/usr/bin/sudo")


def _validate_arguments(
    value: object,
) -> list[str]:
    if not isinstance(value, list):
        raise TypeError("arguments must be a list of strings")

    result: list[str] = []

    for argument in value:
        if not isinstance(argument, str):
            raise TypeError("arguments must contain only strings")

        argument = argument.strip()

        if not argument:
            raise ValueError("arguments cannot contain empty strings")

        result.append(argument)

    return result


def _require_executable(
    path: Path,
    *,
    name: str,
) -> None:
    if not path.is_file():
        raise RuntimeError(f"{name} is missing: {path}")

    if not os.access(
        path,
        os.X_OK,
    ):
        raise RuntimeError(f"{name} is not executable: {path}")


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
    arguments = _validate_arguments(arguments)

    _require_executable(
        BETABOX_EXECUTABLE,
        name="Betabox executable",
    )
    _require_executable(
        SUDO_EXECUTABLE,
        name="sudo",
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
        raise RuntimeError("Unable to elevate Betabox command.") from exc


def require_root_or_elevate(
    arguments: list[str],
) -> None:
    """
    Continue as root or transparently re-execute through sudo.
    """

    if running_as_root():
        return

    elevate_betabox(arguments)
