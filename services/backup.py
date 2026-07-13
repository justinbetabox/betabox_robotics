from __future__ import annotations

import argparse
import json
import shutil
import socket
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from betabox_robotics.version import __version__
from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)

@dataclass(frozen=True)
class BackupItem:
    source: str
    destination: str
    copied: bool
    message: str = ""


@dataclass(frozen=True)
class BackupReport:
    name: str
    path: str
    created_at: str
    hostname: str
    sdk_version: str
    items: list[BackupItem]


def timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def source_paths(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> list[Path]:
    return list(config.paths.backup_sources)


def copy_item(source: Path, backup_dir: Path) -> BackupItem:
    destination = backup_dir / source.as_posix().lstrip("/")

    if not source.exists():
        return BackupItem(
            source=str(source),
            destination=str(destination),
            copied=False,
            message="source missing",
        )

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)

        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)

        return BackupItem(
            source=str(source),
            destination=str(destination),
            copied=True,
            message="copied",
        )

    except Exception as exc:
        return BackupItem(
            source=str(source),
            destination=str(destination),
            copied=False,
            message=str(exc),
        )


def write_manifest(report: BackupReport, backup_dir: Path) -> None:
    manifest = backup_dir / "manifest.json"

    with manifest.open("w") as file:
        json.dump(asdict(report), file, indent=2)


def create_backup(
    name: str | None = None,
    *,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> BackupReport:
    backup_name = name or timestamp()
    backup_dir = config.paths.backup_root / backup_name
    backup_dir.mkdir(parents=True, exist_ok=False)

    items = [
        copy_item(source, backup_dir)
        for source in source_paths(config)
    ]

    report = BackupReport(
        name=backup_name,
        path=str(backup_dir),
        created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        hostname=socket.gethostname(),
        sdk_version=__version__,
        items=items,
    )

    write_manifest(report, backup_dir)
    return report


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


def print_report(report: BackupReport) -> None:
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="betabox backup")
    parser.add_argument("--list", action="store_true", help="List existing backups")
    parser.add_argument("--name", help="Optional backup name")

    args = parser.parse_args(argv)

    if args.list:
        print_backups(list_backups())
        return 0

    try:
        report = create_backup(args.name)
    except FileExistsError:
        print(f"Backup already exists: {args.name}")
        return 1

    print_report(report)
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
