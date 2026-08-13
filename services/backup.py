from __future__ import annotations

import argparse
import socket
import sys
import time
from pathlib import Path
from typing import cast

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.backup_checks import (
    BackupReport,
    copy_item,
    list_backup_directories,
    write_manifest,
)
from betabox_robotics.services.backup_checks.validation import (
    validate_backup_name,
    validate_config,
    validate_path,
)
from betabox_robotics.version import __version__


def _arg_bool(
    value: object,
    *,
    name: str,
) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a boolean")

    return value


def _arg_optional_string(
    value: object,
    *,
    name: str,
) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")

    return value


def timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def source_paths(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> tuple[Path, ...]:
    config_value = validate_config(config)

    return tuple(
        validate_path(
            path,
            name="backup source",
        )
        for path in config_value.paths.backup_sources
    )


def create_backup(
    name: str | None = None,
    *,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> BackupReport:
    config_value = validate_config(config)

    backup_name = validate_backup_name(timestamp() if name is None else name)

    backup_root = validate_path(
        config_value.paths.backup_root,
        name="backup_root",
    )
    backup_dir = backup_root / backup_name

    backup_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    items = tuple(
        copy_item(
            source,
            backup_dir,
        )
        for source in source_paths(config_value)
    )

    report = BackupReport(
        name=backup_name,
        path=str(backup_dir),
        created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        hostname=socket.gethostname(),
        sdk_version=__version__,
        items=items,
    )

    write_manifest(
        report,
        backup_dir,
    )

    return report


def list_backups(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> tuple[Path, ...]:
    config_value = validate_config(config)

    return list_backup_directories(config_value.paths.backup_root)


def print_report(
    report: BackupReport,
) -> None:
    print()
    print("Betabox Backup")
    print("==============")
    print()
    print(f"Name: {report.name}")
    print(f"Path: {report.path}")
    print(f"Created: {report.created_at}")
    print(f"Host: {report.hostname}")
    print(f"SDK: {report.sdk_version}")
    print()
    print("Items")
    print("-----")

    for item in report.items:
        status = "COPIED" if item.copied else "SKIPPED"

        print(f"[{status}] {item.source}")
        print(f"        -> {item.destination}")

        if item.message:
            print(f"        {item.message}")

    print()


def print_backups(
    backups: tuple[Path, ...],
) -> None:
    print()
    print("Betabox Backups")
    print("===============")
    print()

    if not backups:
        print("No backups found.")
        print()
        return

    for path in backups:
        print(path.name)

    print()


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="betabox backup")
    _ = parser.add_argument(
        "--list",
        action="store_true",
        help="List existing backups",
    )
    _ = parser.add_argument(
        "--name",
        help="Optional backup name",
    )

    args = parser.parse_args(argv)

    list_requested = _arg_bool(
        cast(
            object,
            args.list,
        ),
        name="list",
    )

    backup_name = _arg_optional_string(
        cast(
            object,
            args.name,
        ),
        name="name",
    )

    if list_requested:
        print_backups(list_backups())
        return 0

    try:
        report = create_backup(backup_name)
    except (
        TypeError,
        ValueError,
    ) as exc:
        print(str(exc))
        return 1
    except FileExistsError:
        display_name = backup_name if backup_name is not None else "generated timestamp"

        print(f"Backup already exists: {display_name}")
        return 1
    except OSError as exc:
        print(f"Unable to create backup: {exc}")
        return 1

    print_report(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
