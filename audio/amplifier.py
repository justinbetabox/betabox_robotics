from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from typing import Final

SPEAKER_ENABLE_GPIO: Final[int] = 20

PIN_COMMAND_TIMEOUT: Final[float] = 2.0
SPEAKER_WARMUP_TIMEOUT: Final[float] = 2.0
SPEAKER_WARMUP_SECONDS: Final[float] = 0.5

_FALSE_VALUES: Final[frozenset[str]] = frozenset(
    {
        "0",
        "false",
        "no",
        "off",
    }
)


def _validate_pin(
    pin: object,
) -> int:
    if isinstance(pin, bool) or not isinstance(
        pin,
        int,
    ):
        raise TypeError("pin must be an integer")

    if pin < 0:
        raise ValueError("pin cannot be negative")

    return pin


def _environment_flag(
    name: str,
    *,
    default: bool,
) -> bool:
    raw_value = os.environ.get(name)

    if raw_value is None:
        return default

    return raw_value.strip().lower() not in _FALSE_VALUES


def _pin_commands(
    pin: int,
    *,
    high: bool,
) -> tuple[tuple[str, ...], ...]:
    target = "dh" if high else "dl"

    commands: list[tuple[str, ...]] = []

    pinctrl = shutil.which("pinctrl")

    if pinctrl is not None:
        commands.append(
            (
                pinctrl,
                "set",
                str(pin),
                "op",
                target,
            )
        )

    raspi_gpio = shutil.which("raspi-gpio")

    if raspi_gpio is not None:
        commands.append(
            (
                raspi_gpio,
                "set",
                str(pin),
                "op",
                target,
            )
        )

    return tuple(commands)


def _run_command(
    command: tuple[str, ...],
    *,
    timeout: float,
) -> bool:
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=timeout,
        )
    except (
        OSError,
        subprocess.TimeoutExpired,
    ):
        return False

    return result.returncode == 0


def _run_pin_tool(
    pin: int,
    high: bool,
) -> bool:
    pin_number = _validate_pin(pin)

    commands = _pin_commands(
        pin_number,
        high=high,
    )

    if not commands:
        return False

    use_sudo = _environment_flag(
        "BETABOX_AUDIO_SUDO",
        default=True,
    )

    needs_sudo = os.geteuid() != 0 and use_sudo

    for command in commands:
        full_command = (
            (
                "sudo",
                "-n",
                *command,
            )
            if needs_sudo
            else command
        )

        if _run_command(
            full_command,
            timeout=PIN_COMMAND_TIMEOUT,
        ):
            return True

    return False


def _warm_up_speaker() -> None:
    play = shutil.which("play")

    if play is None:
        return

    # Best effort only. Speaker enabling has already succeeded, and a
    # failed SoX warm-up should not make enable_speaker() report failure.
    _run_command(
        (
            play,
            "-n",
            "trim",
            "0.0",
            str(SPEAKER_WARMUP_SECONDS),
        ),
        timeout=SPEAKER_WARMUP_TIMEOUT,
    )


def enable_speaker(
    pin: int = SPEAKER_ENABLE_GPIO,
) -> bool:
    enabled = _run_pin_tool(
        pin,
        high=True,
    )

    if enabled:
        _warm_up_speaker()

    return enabled


def disable_speaker(
    pin: int = SPEAKER_ENABLE_GPIO,
) -> bool:
    return _run_pin_tool(
        pin,
        high=False,
    )


@contextmanager
def speaker_on(
    pin: int = SPEAKER_ENABLE_GPIO,
) -> Generator[bool, None, None]:
    """
    Enable the speaker for the duration of the context.

    The yielded value reports whether speaker enabling succeeded.
    Speaker disabling is attempted on context exit regardless of whether
    the body succeeds.
    """

    enabled = enable_speaker(pin)

    try:
        yield enabled
    finally:
        disable_speaker(pin)
