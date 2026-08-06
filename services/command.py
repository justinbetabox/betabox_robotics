from __future__ import annotations

import math
import subprocess


def _validate_command(
    value: object,
) -> list[str]:
    if not isinstance(value, list):
        raise TypeError("command must be a list of strings")

    result: list[str] = []

    for argument in value:
        if not isinstance(argument, str):
            raise TypeError("command must contain only strings")

        cleaned = argument.strip()

        if not cleaned:
            raise ValueError("command cannot contain empty strings")

        result.append(cleaned)

    if not result:
        raise ValueError("command cannot be empty")

    return result


def _validate_timeout(
    value: object,
) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        int | float,
    ):
        raise TypeError("timeout must be a number")

    result = float(value)

    if not math.isfinite(result):
        raise ValueError("timeout must be finite")

    if result <= 0:
        raise ValueError("timeout must be greater than 0")

    return result


def run(
    command: list[str],
    *,
    timeout: float = 5.0,
) -> subprocess.CompletedProcess[str] | None:
    """
    Run a non-interactive command.

    Return None when the command cannot be launched or
    exceeds the configured timeout.
    """

    command_value = _validate_command(command)
    timeout_value = _validate_timeout(timeout)

    try:
        return subprocess.run(
            command_value,
            capture_output=True,
            text=True,
            timeout=timeout_value,
            check=False,
        )
    except (
        OSError,
        subprocess.TimeoutExpired,
    ):
        return None
