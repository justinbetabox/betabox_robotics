from __future__ import annotations

import shutil
from pathlib import Path

from betabox_robotics.services.backup_checks.validation import (
    validate_path,
)

from .models import RestoreItem


def backup_source_path(
    backup_dir: str | Path,
    destination: str | Path,
) -> Path:
    """
    Return the source path inside a backup for one
    absolute or relative restore destination.
    """

    backup_dir_value = validate_path(
        backup_dir,
        name="backup_dir",
    )
    destination_value = validate_path(
        destination,
        name="destination",
    )

    return backup_dir_value / destination_value.as_posix().lstrip("/")


def restore_item(
    backup_dir: str | Path,
    destination: str | Path,
    *,
    dry_run: bool,
) -> RestoreItem:
    """
    Restore one path from a backup directory.

    Missing backup sources, dry runs, and expected
    filesystem errors are represented in the result.
    """

    if not isinstance(
        dry_run,
        bool,
    ):
        raise TypeError("dry_run must be a boolean")

    backup_dir_value = validate_path(
        backup_dir,
        name="backup_dir",
    )
    destination_value = validate_path(
        destination,
        name="destination",
    )
    source = backup_source_path(
        backup_dir_value,
        destination_value,
    )

    if not source.exists():
        return RestoreItem(
            source=str(source),
            destination=str(destination_value),
            restored=False,
            message="source missing in backup",
        )

    if dry_run:
        return RestoreItem(
            source=str(source),
            destination=str(destination_value),
            restored=False,
            message="dry run",
        )

    try:
        destination_value.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if source.is_dir():
            shutil.copytree(
                source,
                destination_value,
                dirs_exist_ok=True,
            )
        else:
            shutil.copy2(
                source,
                destination_value,
            )

    except OSError as exc:
        return RestoreItem(
            source=str(source),
            destination=str(destination_value),
            restored=False,
            message=str(exc),
        )

    return RestoreItem(
        source=str(source),
        destination=str(destination_value),
        restored=True,
        message="restored",
    )
