from __future__ import annotations

import argparse
import os
import pwd
import sys
from pathlib import Path

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.accounts import (
    BETABOX_ACCOUNTS,
)
from betabox_robotics.services.install_checks import (
    CheckResult,
    check_account_workspace,
    check_avahi_override,
    check_command,
    check_config_line,
    check_executable,
    check_import,
    check_runtime_media,
    check_service_enabled,
    check_service_installed,
)
from betabox_robotics.services.install_checks.validation import (
    validate_checks,
    validate_config,
    validate_optional_string,
    validate_string,
)


def resolve_service_user(
    requested_user: str | None = None,
) -> str:
    requested_user_value = validate_optional_string(
        requested_user,
        name="requested_user",
    )

    if requested_user_value is not None:
        return requested_user_value

    sudo_user = os.environ.get("SUDO_USER")

    if sudo_user is not None:
        sudo_user_value = sudo_user.strip()

        if sudo_user_value:
            return validate_string(
                sudo_user_value,
                name="SUDO_USER",
            )

    user = pwd.getpwuid(os.getuid())

    return validate_string(
        user.pw_name,
        name="service user",
    )


def collect_checks(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
    *,
    service_user: str,
) -> tuple[CheckResult, ...]:
    config_value = validate_config(config)
    service_user_value = validate_string(
        service_user,
        name="service_user",
    )

    betabox_command = str(Path(sys.executable).parent / "betabox")

    checks: list[CheckResult] = []
    verification = config_value.verification

    for module in verification.required_python_modules:
        checks.append(check_import(module))

    checks.append(
        check_command(
            [
                betabox_command,
                "--help",
            ],
            "cli:betabox",
            timeout=(verification.command_timeout_seconds),
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
            timeout=(verification.command_timeout_seconds),
        )
    )

    for line in verification.required_boot_config_lines:
        checks.append(
            check_config_line(
                line,
                config_value,
            )
        )

    for account in BETABOX_ACCOUNTS:
        checks.append(
            check_account_workspace(
                account.username,
                account.home,
            )
        )

    checks.append(check_runtime_media(service_user_value))

    for executable in verification.required_executables:
        checks.append(check_executable(executable))

    for unit in config_value.services.all_units:
        checks.append(check_service_installed(unit))
        checks.append(
            check_service_enabled(
                unit,
                timeout=(verification.command_timeout_seconds),
            )
        )

    checks.append(check_avahi_override())

    return tuple(checks)


def print_results(
    checks: tuple[CheckResult, ...],
) -> bool:
    checks_value = validate_checks(checks)

    print()
    print("Betabox Install Check")
    print("=====================")
    print()

    all_ok = True

    for check in checks_value:
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
        description=("Verify the Betabox software installation."),
    )

    parser.add_argument(
        "--service-user",
        help=(
            "Linux account used by Betabox "
            "services. Defaults to SUDO_USER "
            "when run through sudo."
        ),
    )

    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
) -> int:
    args = parse_args(argv)

    try:
        service_user = resolve_service_user(args.service_user)
        checks = collect_checks(
            DEFAULT_PLATFORM_CONFIG,
            service_user=service_user,
        )
    except (
        TypeError,
        ValueError,
        KeyError,
        OSError,
    ) as exc:
        print(str(exc))
        return 1

    return 0 if print_results(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
