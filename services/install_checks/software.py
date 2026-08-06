from __future__ import annotations

import importlib
import shutil

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.command import run

from .models import CheckResult
from .validation import (
    validate_command,
    validate_config,
    validate_path,
    validate_string,
    validate_timeout,
)


def check_import(
    module: str,
) -> CheckResult:
    """
    Verify that a Python module can be imported.
    """

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
    """
    Run one installation verification command.
    """

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


def check_config_line(
    line: str,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> CheckResult:
    """
    Verify that one required line exists in the boot
    configuration file.
    """

    line_value = validate_string(
        line,
        name="line",
    )
    config_value = validate_config(config)
    config_file = validate_path(
        config_value.verification.boot_config_file,
        name="boot_config_file",
    )
    check_name = f"config:{line_value}"

    if not config_file.exists():
        return CheckResult(
            name=check_name,
            ok=False,
            message=f"{config_file} missing",
        )

    try:
        text = config_file.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError as exc:
        return CheckResult(
            name=check_name,
            ok=False,
            message=str(exc),
        )

    present = line_value in text

    return CheckResult(
        name=check_name,
        ok=present,
        message=("present" if present else "missing"),
    )


def check_executable(
    command: str,
) -> CheckResult:
    """
    Verify that an executable is available on PATH.
    """

    command_value = validate_string(
        command,
        name="command",
    )
    path = shutil.which(command_value)

    return CheckResult(
        name=f"command:{command_value}",
        ok=path is not None,
        message=(path if path is not None else "not found"),
    )
