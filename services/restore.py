from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)


@dataclass(frozen=True)
class RestoreItem:
    source: str
    destination: str
    restored: bool
    message: str = ""


def list_backups(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> list[Path]:
    backup_root = config.paths.backup_root

    if not backup_root.exists():
        return []

    return sorted(
        [
            path
            for path in backup_root.iterdir()
            if path.is_dir()
        ],
        reverse=True,
    )


def backup_path(
    name: str,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> Path:
    return config.paths.backup_root / name


def backup_source_path(backup_dir: Path, destination: Path) -> Path:
    return backup_dir / destination.as_posix().lstrip("/")


def restore_item(backup_dir: Path, destination: Path, *, dry_run: bool) -> RestoreItem:
    source = backup_source_path(backup_dir, destination)

    if not source.exists():
        return RestoreItem(
            source=str(source),
            destination=str(destination),
            restored=False,
            message="source missing in backup",
        )

    if dry_run:
        return RestoreItem(
            source=str(source),
            destination=str(destination),
            restored=False,
            message="dry run",
        )

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)

        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)

        return RestoreItem(
            source=str(source),
            destination=str(destination),
            restored=True,
            message="restored",
        )

    except Exception as exc:
        return RestoreItem(
            source=str(source),
            destination=str(destination),
            restored=False,
            message=str(exc),
        )


def restore_backup(
    name: str,
    *,
    dry_run: bool = False,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> list[RestoreItem]:
    backup_dir = backup_path(name, config)

    if not backup_dir.exists():
        raise FileNotFoundError(f"Backup not found: {name}")

    return [
        restore_item(
            backup_dir,
            destination,
            dry_run=dry_run,
        )
        for destination in config.paths.restore_paths
    ]


def print_backups(backups: list[Path]) -> None:
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


def print_report(name: str, items: list[RestoreItem], *, dry_run: bool) -> None:
    print()
    print("Betabox Restore")
    print("===============")
    print()
    print(f"Backup: {name}")
    print(f"Mode:   {'dry-run' if dry_run else 'restore'}")
    print()
    print("Items")
    print("-----")

    for item in items:
        if dry_run:
            status = "WOULD RESTORE" if Path(item.source).exists() else "SKIP"
        else:
            status = "RESTORED" if item.restored else "SKIPPED"

        print(f"[{status}] {item.source}")
        print(f"          -> {item.destination}")

        if item.message:
            print(f"          {item.message}")

    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="betabox restore")
    parser.add_argument("name", nargs="?", help="Backup name to restore")
    parser.add_argument("--list", action="store_true", help="List available backups")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be restored"
    )

    args = parser.parse_args(argv)

    if args.list or not args.name:
        print_backups(list_backups())
        return 0

    try:
        items = restore_backup(args.name, dry_run=args.dry_run)
    except FileNotFoundError as exc:
        print(exc)
        return 1

    print_report(args.name, items, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
