from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path

from betabox_robotics.services.backup import create_backup
from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)


@dataclass(frozen=True)
class ResetItem:
    path: str
    action: str
    ok: bool
    message: str = ""


def remove_path(path: Path, *, dry_run: bool) -> ResetItem:
    if not path.exists():
        return ResetItem(
            path=str(path),
            action="skip",
            ok=True,
            message="missing",
        )

    if dry_run:
        return ResetItem(
            path=str(path),
            action="would remove",
            ok=True,
            message="dry run",
        )

    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

        return ResetItem(
            path=str(path),
            action="removed",
            ok=True,
            message="",
        )

    except Exception as exc:
        return ResetItem(
            path=str(path),
            action="remove failed",
            ok=False,
            message=str(exc),
        )


def recreate_path(path: Path, *, dry_run: bool) -> ResetItem:
    if dry_run:
        return ResetItem(
            path=str(path),
            action="would recreate",
            ok=True,
            message="dry run",
        )

    try:
        path.mkdir(parents=True, exist_ok=True)
        return ResetItem(
            path=str(path),
            action="recreated",
            ok=True,
            message="",
        )
    except Exception as exc:
        return ResetItem(
            path=str(path),
            action="recreate failed",
            ok=False,
            message=str(exc),
        )


def run_reset(
    *,
    dry_run: bool,
    backup: bool,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> tuple[str | None, list[ResetItem]]:
    backup_name: str | None = None

    if backup and not dry_run:
        report = create_backup(
            name=None,
            config=config,
        )
        backup_name = report.name

    items: list[ResetItem] = []

    for path in config.paths.reset_paths:
        items.append(
            remove_path(
                path,
                dry_run=dry_run,
            )
        )

    for path in config.paths.recreate_paths:
        items.append(
            recreate_path(
                path,
                dry_run=dry_run,
            )
        )

    return backup_name, items


def print_report(
    *, dry_run: bool, backup_name: str | None, items: list[ResetItem]
) -> bool:
    print()
    print("Betabox Reset")
    print("=============")
    print()
    print(f"Mode:   {'dry-run' if dry_run else 'reset'}")

    if backup_name:
        print(f"Backup: {backup_name}")
    elif dry_run:
        print("Backup: would create backup before reset")
    else:
        print("Backup: skipped")

    print()
    print("Items")
    print("-----")

    all_ok = True

    for item in items:
        status = "OK" if item.ok else "FAIL"
        print(f"[{status}] {item.action}: {item.path}")

        if item.message:
            print(f"     {item.message}")

        if not item.ok:
            all_ok = False

    print()

    if all_ok:
        print(
            "Reset completed successfully."
            if not dry_run
            else "Dry run completed successfully."
        )
    else:
        print("Reset completed with errors.")

    print()
    return all_ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="betabox reset")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be reset"
    )
    parser.add_argument("--yes", action="store_true", help="Confirm reset")
    parser.add_argument(
        "--no-backup", action="store_true", help="Skip automatic backup"
    )

    args = parser.parse_args(argv)

    if not args.dry_run and not args.yes:
        print()
        print("This command removes generated Betabox media.")
        print()
        print("Run a preview first:")
        print("  betabox reset --dry-run")
        print()
        print("To perform the reset:")
        print("  betabox reset --yes")
        print()
        return 1

    backup_name, items = run_reset(
        dry_run=args.dry_run,
        backup=not args.no_backup,
    )

    return (
        0
        if print_report(
            dry_run=args.dry_run,
            backup_name=backup_name,
            items=items,
        )
        else 1
    )


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
