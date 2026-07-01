import os
import shutil
import subprocess
from contextlib import contextmanager

SPEAKER_ENABLE_GPIO = 20


def _run_pin_tool(pin: int, high: bool) -> bool:
    target = "dh" if high else "dl"

    commands: list[list[str]] = []

    if shutil.which("pinctrl"):
        commands.append(["pinctrl", "set", str(pin), "op", target])

    if shutil.which("raspi-gpio"):
        commands.append(["raspi-gpio", "set", str(pin), "op", target])

    if not commands:
        return False

    use_sudo = os.environ.get("BETABOX_AUDIO_SUDO", "1") not in (
        "0",
        "false",
        "False",
        "no",
        "NO",
    )

    for command in commands:
        full_command = command

        if os.geteuid() != 0 and use_sudo:
            full_command = ["sudo", "-n", *command]

        result = subprocess.run(
            full_command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if result.returncode == 0:
            return True

    return False


def enable_speaker(pin: int = SPEAKER_ENABLE_GPIO) -> bool:
    ok = _run_pin_tool(pin, high=True)

    if ok and shutil.which("play"):
        subprocess.run(
            ["play", "-n", "trim", "0.0", "0.5"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    return ok


def disable_speaker(pin: int = SPEAKER_ENABLE_GPIO) -> bool:
    return _run_pin_tool(pin, high=False)


@contextmanager
def speaker_on(pin: int = SPEAKER_ENABLE_GPIO):
    enable_speaker(pin)
    try:
        yield
    finally:
        disable_speaker(pin)
