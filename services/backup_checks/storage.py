from __future__ import annotations

import json
import shutil
from pathlib import Path

from .models import (
    BackupItem,
    BackupReport,
)
from .validation import validate_path


def copy_item(
    source: str | Path,
    backup_dir: str | Path,
) -> BackupItem:
    """
    Copy one backup source into the backup directory.

    Missing sources and expected filesystem failures are
    represented in the returned BackupItem.
    """

    source_value = validate_path(
        source,
        name="source",
    )
    backup_dir_value = validate_path(
        backup_dir,
        name="backup_dir",
    )

    destination = backup_dir_value / source_value.as_posix().lstrip("/")

    if not source_value.exists():
        return BackupItem(
            source=str(source_value),
            destination=str(destination),
            copied=False,
            message="source missing",
        )

    try:
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if source_value.is_dir():
            shutil.copytree(
                source_value,
                destination,
                dirs_exist_ok=True,
            )
        else:
            shutil.copy2(
                source_value,
                destination,
            )

    except OSError as exc:
        return BackupItem(
            source=str(source_value),
            destination=str(destination),
            copied=False,
            message=str(exc),
        )

    return BackupItem(
        source=str(source_value),
        destination=str(destination),
        copied=True,
        message="copied",
    )


def write_manifest(
    report: BackupReport,
    backup_dir: str | Path,
) -> None:
    """
    Write a backup report to manifest.json.
    """

    if not isinstance(
        report,
        BackupReport,
    ):
        raise TypeError("report must be a BackupReport")

    backup_dir_value = validate_path(
        backup_dir,
        name="backup_dir",
    )
    manifest = backup_dir_value / "manifest.json"

    with manifest.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report.to_dict(),
            file,
            indent=2,
        )
        file.write("\n")


def list_backup_directories(
    backup_root: str | Path,
) -> tuple[Path, ...]:
    """
    Return backup directories sorted newest-name first.

    Missing or unreadable roots return an empty tuple.
    """

    backup_root_value = validate_path(
        backup_root,
        name="backup_root",
    )

    if not backup_root_value.exists():
        return ()

    try:
        backups = tuple(path for path in backup_root_value.iterdir() if path.is_dir())
    except OSError:
        return ()

    return tuple(
        sorted(
            backups,
            reverse=True,
        )
    )
