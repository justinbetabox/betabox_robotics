from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.backup import create_backup


def _validate_config(
    value: object,
) -> PlatformConfig:
    if not isinstance(
        value,
        PlatformConfig,
    ):
        raise TypeError("config must be a PlatformConfig")

    return value


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


@dataclass(frozen=True, slots=True)
class ResetItem:
    path: str
    action: str
    ok: bool
    message: str = ""

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "path",
            str(
                _validate_path(
                    self.path,
                    name="path",
                )
            ),
        )

        for name in (
            "action",
            "message",
        ):
            value = cast(
                object,
                getattr(
                    self,
                    name,
                ),
            )

            if not isinstance(
                value,
                str,
            ):
                raise TypeError(f"{name} must be a string")

            result = value.strip()

            if name == "action" and not result:
                raise ValueError("action cannot be empty")

            object.__setattr__(
                self,
                name,
                result,
            )


def _validate_items(
    value: object,
) -> tuple[ResetItem, ...]:
    if not isinstance(
        value,
        tuple,
    ):
        raise TypeError("items must be a tuple")

    items = cast(
        tuple[object, ...],
        value,
    )

    if not all(isinstance(item, ResetItem) for item in items):
        raise TypeError("items must contain only ResetItem values")

    return cast(
        tuple[ResetItem, ...],
        items,
    )


def remove_path(
    path: str | Path,
    *,
    dry_run: bool,
) -> ResetItem:
    path_value = _validate_path(
        path,
        name="path",
    )
    dry_run_value = _validate_flag(
        dry_run,
        name="dry_run",
    )

    try:
        exists = path_value.exists()
    except OSError as exc:
        return ResetItem(
            path=str(path_value),
            action="remove failed",
            ok=False,
            message=str(exc),
        )

    if not exists:
        return ResetItem(
            path=str(path_value),
            action="skip",
            ok=True,
            message="missing",
        )

    if dry_run_value:
        return ResetItem(
            path=str(path_value),
            action="would remove",
            ok=True,
            message="dry run",
        )

    try:
        if path_value.is_dir():
            shutil.rmtree(path_value)
        else:
            path_value.unlink()

        return ResetItem(
            path=str(path_value),
            action="removed",
            ok=True,
        )

    except OSError as exc:
        return ResetItem(
            path=str(path_value),
            action="remove failed",
            ok=False,
            message=str(exc),
        )


def recreate_path(
    path: str | Path,
    *,
    dry_run: bool,
) -> ResetItem:
    path_value = _validate_path(
        path,
        name="path",
    )
    dry_run_value = _validate_flag(
        dry_run,
        name="dry_run",
    )

    if dry_run_value:
        return ResetItem(
            path=str(path_value),
            action="would recreate",
            ok=True,
            message="dry run",
        )

    try:
        path_value.mkdir(
            parents=True,
            exist_ok=True,
        )

        return ResetItem(
            path=str(path_value),
            action="recreated",
            ok=True,
        )

    except OSError as exc:
        return ResetItem(
            path=str(path_value),
            action="recreate failed",
            ok=False,
            message=str(exc),
        )


def run_reset(
    *,
    dry_run: bool,
    backup: bool,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> tuple[
    str | None,
    tuple[ResetItem, ...],
]:
    dry_run_value = _validate_flag(
        dry_run,
        name="dry_run",
    )
    backup_value = _validate_flag(
        backup,
        name="backup",
    )
    config_value = _validate_config(config)

    backup_name: str | None = None

    if backup_value and not dry_run_value:
        report = create_backup(
            name=None,
            config=config_value,
        )
        backup_name = report.name

    items = (
        *(
            remove_path(
                path,
                dry_run=dry_run_value,
            )
            for path in (config_value.paths.reset_paths)
        ),
        *(
            recreate_path(
                path,
                dry_run=dry_run_value,
            )
            for path in (config_value.paths.recreate_paths)
        ),
    )

    return (
        backup_name,
        items,
    )


def print_report(
    *,
    dry_run: bool,
    backup: bool,
    backup_name: str | None,
    items: tuple[ResetItem, ...],
) -> bool:
    dry_run_value = _validate_flag(
        dry_run,
        name="dry_run",
    )
    items_value = _validate_items(items)

    backup_value = _validate_flag(
        backup,
        name="backup",
    )

    if backup_name is not None:
        backup_name_value = backup_name.strip()

        if not backup_name_value:
            raise ValueError("backup_name cannot be empty")
    else:
        backup_name_value = None

    print()
    print("Betabox Reset")
    print("=============")
    print()
    print(f"Mode:   {'dry-run' if dry_run_value else 'reset'}")

    if backup_name_value:
        print(f"Backup: {backup_name_value}")
    elif backup_value and dry_run_value:
        print("Backup: would create backup before reset")
    else:
        print("Backup: skipped")

    print()
    print("Items")
    print("-----")

    all_ok = True

    for item in items_value:
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
            if not dry_run_value
            else "Dry run completed successfully."
        )
    else:
        print("Reset completed with errors.")

    print()
    return all_ok


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="betabox reset")

    _ = parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be reset",
    )
    _ = parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm reset",
    )
    _ = parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip automatic backup",
    )

    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
) -> int:
    args = parse_args(argv)

    try:
        dry_run = _validate_flag(
            cast(
                object,
                args.dry_run,
            ),
            name="dry_run",
        )

        confirmed = _validate_flag(
            cast(
                object,
                args.yes,
            ),
            name="yes",
        )

        no_backup = _validate_flag(
            cast(
                object,
                args.no_backup,
            ),
            name="no_backup",
        )

        if not dry_run and not confirmed:
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

        backup_requested = not no_backup

        backup_name, items = run_reset(
            dry_run=dry_run,
            backup=backup_requested,
        )

        success = print_report(
            dry_run=dry_run,
            backup=backup_requested,
            backup_name=backup_name,
            items=items,
        )

    except (
        TypeError,
        ValueError,
        OSError,
    ) as exc:
        print(str(exc))
        return 1

    return 0 if success else 1


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
