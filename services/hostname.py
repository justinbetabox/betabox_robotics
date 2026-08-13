from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.command import run
from betabox_robotics.services.identity import (
    identity_name,
)

DEFAULT_HOSTS_PATH = Path("/etc/hosts")


def _validate_config(
    value: object,
) -> PlatformConfig:
    if not isinstance(
        value,
        PlatformConfig,
    ):
        raise TypeError("config must be a PlatformConfig")

    return value


def _validate_string(
    value: object,
    *,
    name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(f"{name} must be a string")

    result = value.strip()

    if not result:
        raise ValueError(f"{name} cannot be empty")

    return result


def _validate_path(
    value: object,
    *,
    name: str,
) -> Path:
    if isinstance(value, bool) or not isinstance(
        value,
        str | Path,
    ):
        raise TypeError(f"{name} must be a string or Path")

    if isinstance(value, str):
        value = value.strip()

        if not value:
            raise ValueError(f"{name} cannot be empty")

    return Path(value).expanduser()


def _validate_flag(
    value: object,
    *,
    name: str,
) -> bool:
    if not isinstance(
        value,
        bool,
    ):
        raise TypeError(f"{name} must be a boolean")

    return value


def desired_hostname(
    prefix: str,
) -> str | None:
    prefix_value = _validate_string(
        prefix,
        name="prefix",
    )

    return identity_name(prefix_value)


def current_hostname() -> str:
    result = run(
        [
            "hostname",
        ],
        timeout=5,
    )

    if result is None:
        raise OSError("hostname command failed to run")

    if result.returncode != 0:
        raise OSError(
            result.stderr.strip() or result.stdout.strip() or "hostname command failed"
        )

    hostname = result.stdout.strip()

    if not hostname:
        raise OSError("hostname command returned no hostname")

    return hostname


def update_hosts_file(
    hostname: str,
    *,
    dry_run: bool = False,
    path: str | Path = DEFAULT_HOSTS_PATH,
) -> None:
    hostname_value = _validate_string(
        hostname,
        name="hostname",
    )
    dry_run_value = _validate_flag(
        dry_run,
        name="dry_run",
    )
    path_value = _validate_path(
        path,
        name="path",
    )

    if dry_run_value:
        print(f"Would update {path_value} 127.0.1.1 entry to {hostname_value}")
        return

    lines = path_value.read_text(
        encoding="utf-8",
        errors="ignore",
    ).splitlines()

    updated = False
    new_lines: list[str] = []

    for line in lines:
        fields = line.split()

        if fields and fields[0] == "127.0.1.1":
            new_lines.append(f"127.0.1.1\t{hostname_value}")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"127.0.1.1\t{hostname_value}")

    _ = path_value.write_text(
        "\n".join(new_lines) + "\n",
        encoding="utf-8",
    )


def set_hostname(
    *,
    prefix: str | None = None,
    dry_run: bool = False,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> int:
    config_value = _validate_config(config)
    dry_run_value = _validate_flag(
        dry_run,
        name="dry_run",
    )

    selected_prefix = config_value.network.identity_prefix if prefix is None else prefix
    prefix_value = _validate_string(
        selected_prefix,
        name="prefix",
    )

    new_hostname = desired_hostname(prefix_value)

    if new_hostname is None:
        print("Could not determine serial; leaving hostname unchanged.")
        return 0

    new_hostname_value = _validate_string(
        new_hostname,
        name="hostname",
    )
    old_hostname = current_hostname()

    if old_hostname == new_hostname_value:
        print(f"Hostname already correct: {old_hostname}")
        return 0

    print(f"Changing hostname from {old_hostname} to {new_hostname_value}")

    if dry_run_value:
        print(f"Would run: hostnamectl set-hostname {new_hostname_value}")
        update_hosts_file(
            new_hostname_value,
            dry_run=True,
        )
        return 0

    result = run(
        [
            "hostnamectl",
            "set-hostname",
            new_hostname_value,
        ],
        timeout=5,
    )

    if result is None:
        print("hostnamectl failed to run")
        return 1

    if result.returncode != 0:
        print(result.stderr.strip() or result.stdout.strip() or "hostnamectl failed")
        return result.returncode if result.returncode > 0 else 1

    update_hosts_file(new_hostname_value)

    return 0


def parse_args(
    argv: list[str] | None = None,
    *,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> argparse.Namespace:
    config_value = _validate_config(config)

    parser = argparse.ArgumentParser(prog="betabox set-hostname")

    _ = parser.add_argument(
        "--prefix",
        default=(config_value.network.identity_prefix),
    )
    _ = parser.add_argument(
        "--dry-run",
        action="store_true",
    )

    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
) -> int:
    config = DEFAULT_PLATFORM_CONFIG
    args = parse_args(
        argv,
        config=config,
    )

    try:
        raw_prefix = cast(
            object,
            args.prefix,
        )

        prefix = (
            None
            if raw_prefix is None
            else _validate_string(
                raw_prefix,
                name="prefix",
            )
        )

        dry_run = _validate_flag(
            cast(
                object,
                args.dry_run,
            ),
            name="dry_run",
        )

        return set_hostname(
            prefix=prefix,
            dry_run=dry_run,
            config=config,
        )

    except (
        TypeError,
        ValueError,
        OSError,
    ) as exc:
        print(str(exc))
        return 1
