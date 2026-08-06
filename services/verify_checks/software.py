from __future__ import annotations

import importlib

from betabox_robotics.services.command import run

from .models import CheckResult
from .validation import (
    validate_command,
    validate_string,
    validate_timeout,
)


def check_import(
    module: str,
) -> CheckResult:
    module_value = validate_string(
        module,
        name="module",
    )

    try:
        imported = importlib.import_module(module_value)
    except (
        ImportError,
        ModuleNotFoundError,
    ) as exc:
        return CheckResult(
            name=f"import:{module_value}",
            ok=False,
            message=str(exc),
        )

    version = getattr(
        imported,
        "__version__",
        "",
    )

    message = str(version).strip() if version is not None else ""

    return CheckResult(
        name=f"import:{module_value}",
        ok=True,
        message=message or "import ok",
    )


def check_command(
    command: list[str],
    name: str,
    *,
    timeout: int = 5,
) -> CheckResult:
    command_value = validate_command(command)
    name_value = validate_string(
        name,
        name="name",
    )
    timeout_value = validate_timeout(timeout)

    result = run(
        command_value,
        timeout=timeout_value,
    )

    if result is None:
        return CheckResult(
            name=name_value,
            ok=False,
            message="command failed to run",
        )

    message = (
        result.stdout.strip()
        or result.stderr.strip()
        or ("command succeeded" if result.returncode == 0 else "command failed")
    )

    return CheckResult(
        name=name_value,
        ok=result.returncode == 0,
        message=message,
    )


def check_picamera2() -> CheckResult:
    result = check_import("picamera2")

    return CheckResult(
        name="camera:picamera2",
        ok=result.ok,
        message=result.message,
    )


def check_configurable_http_proxy(
    *,
    timeout: int = 5,
) -> CheckResult:
    timeout_value = validate_timeout(timeout)

    result = check_command(
        [
            "configurable-http-proxy",
            "--version",
        ],
        "jupyterhub:proxy",
        timeout=timeout_value,
    )

    if not result.ok:
        return CheckResult(
            name="jupyterhub:proxy",
            ok=False,
            message=("configurable-http-proxy not installed"),
        )

    return CheckResult(
        name="jupyterhub:proxy",
        ok=True,
        message=(
            result.message
            if result.message
            not in {
                "command succeeded",
            }
            else "installed"
        ),
    )


def check_speech_backend() -> CheckResult:
    try:
        from betabox_robotics.audio.speech import (
            available_backends,
        )

        backends = tuple(
            validate_string(
                backend,
                name="speech backend",
            )
            for backend in available_backends()
        )

    except (
        ImportError,
        ModuleNotFoundError,
    ) as exc:
        return CheckResult(
            name="audio:speech_backend",
            ok=False,
            message=str(exc),
        )

    if not backends:
        return CheckResult(
            name="audio:speech_backend",
            ok=False,
            message="no speech backends found",
        )

    return CheckResult(
        name="audio:speech_backend",
        ok=True,
        message=", ".join(backends),
    )
