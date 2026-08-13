from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import cast

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.backup_checks import (
    list_backup_directories,
)
from betabox_robotics.services.backup_checks.validation import (
    validate_backup_name,
    validate_config,
    validate_path,
)
from betabox_robotics.services.restore_checks import (
    RestoreItem,
    restore_item,
)


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


def list_backups(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> tuple[Path, ...]:
    config_value = validate_config(config)

    return list_backup_directories(config_value.paths.backup_root)


def backup_path(
    name: str,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> Path:
    config_value = validate_config(config)
    backup_name = validate_backup_name(name)

    backup_root = validate_path(
        config_value.paths.backup_root,
        name="backup_root",
    )

    return backup_root / backup_name


def restore_backup(
    name: str,
    *,
    dry_run: bool = False,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> tuple[RestoreItem, ...]:
    config_value = validate_config(config)

    dry_run_value = _validate_flag(
        dry_run,
        name="dry_run",
    )

    backup_dir = backup_path(
        name,
        config_value,
    )

    if not backup_dir.exists():
        raise FileNotFoundError(f"Backup not found: {name}")

    return tuple(
        restore_item(
            backup_dir,
            destination,
            dry_run=dry_run_value,
        )
        for destination in config_value.paths.restore_paths
    )


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


def print_report(
    name: str,
    items: tuple[RestoreItem, ...],
    *,
    dry_run: bool,
) -> None:
    backup_name = validate_backup_name(name)

    dry_run_value = _validate_flag(
        dry_run,
        name="dry_run",
    )

    print()
    print("Betabox Restore")
    print("===============")
    print()
    print(f"Backup: {backup_name}")
    print(f"Mode:   {'dry-run' if dry_run_value else 'restore'}")
    print()
    print("Items")
    print("-----")

    for item in items:
        if dry_run_value:
            status = "WOULD RESTORE" if item.message == "dry run" else "SKIP"
        else:
            status = "RESTORED" if item.restored else "SKIPPED"

        print(f"[{status}] {item.source}")
        print(f"          -> {item.destination}")

        if item.message:
            print(f"          {item.message}")

    print()


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        prog="betabox restore",
    )

    _ = parser.add_argument(
        "name",
        nargs="?",
        help="Backup name to restore",
    )

    _ = parser.add_argument(
        "--list",
        action="store_true",
        help="List available backups",
    )

    _ = parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be restored",
    )

    args = parser.parse_args(argv)

    try:
        list_requested = _validate_flag(
            cast(
                object,
                args.list,
            ),
            name="list",
        )

        dry_run = _validate_flag(
            cast(
                object,
                args.dry_run,
            ),
            name="dry_run",
        )

        raw_name = cast(
            object,
            args.name,
        )

        name = None if raw_name is None else validate_backup_name(raw_name)

    except (
        TypeError,
        ValueError,
    ) as exc:
        print(str(exc))
        return 1

    if list_requested or name is None:
        print_backups(list_backups())
        return 0

    try:
        items = restore_backup(
            name,
            dry_run=dry_run,
        )

    except (
        TypeError,
        ValueError,
        FileNotFoundError,
    ) as exc:
        print(str(exc))
        return 1

    except OSError as exc:
        print(f"Unable to restore backup: {exc}")
        return 1

    try:
        print_report(
            name,
            items,
            dry_run=dry_run,
        )

    except (
        TypeError,
        ValueError,
        OSError,
    ) as exc:
        print(str(exc))
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
