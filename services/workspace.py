from __future__ import annotations

import grp
import os
import pwd
import shutil
from collections.abc import Iterable
from pathlib import Path

from betabox_robotics.services.accounts import (
    BETABOX_ACCOUNTS,
    BETABOX_SHARED_GROUP,
    ProvisionedAccount,
)

WORKSPACE_MODE = 0o2770


def _validate_string(
    value: object,
    *,
    name: str,
) -> str:
    if not isinstance(value, str):
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

    return Path(value).expanduser()


def _validate_id(
    value: object,
    *,
    name: str,
) -> int:
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError(f"{name} must be an integer")

    if value < 0:
        raise ValueError(f"{name} cannot be negative")

    return value


def account_ids(
    username: str,
) -> tuple[int, int]:
    """Return the UID and primary GID for an account."""

    username_value = _validate_string(
        username,
        name="username",
    )

    try:
        account = pwd.getpwnam(username_value)
    except KeyError as exc:
        raise RuntimeError(f"Linux account does not exist: {username_value}") from exc

    return (
        account.pw_uid,
        account.pw_gid,
    )


def group_id(
    group_name: str,
) -> int:
    """Return the GID for a Linux group."""

    group_value = _validate_string(
        group_name,
        name="group_name",
    )

    try:
        group = grp.getgrnam(group_value)
    except KeyError as exc:
        raise RuntimeError(f"Linux group does not exist: {group_value}") from exc

    return group.gr_gid


def workspace_directories(
    account: ProvisionedAccount,
) -> tuple[Path, ...]:
    """Return all directories in an account workspace."""
    media = account.home / "media"

    return (
        account.home / "curriculum",
        media,
        media / "pictures",
        media / "videos",
        media / "sounds",
        account.home / ".config" / "betabox" / "preferences",
    )


def ensure_directory(
    directory: str | Path,
    *,
    uid: int,
    gid: int,
) -> None:
    """Create and configure one workspace directory."""

    directory_path = _validate_path(
        directory,
        name="directory",
    )
    uid_value = _validate_id(
        uid,
        name="uid",
    )
    gid_value = _validate_id(
        gid,
        name="gid",
    )

    directory_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not directory_path.is_dir():
        raise NotADirectoryError(f"Workspace path is not a directory: {directory_path}")

    _set_ownership(
        directory_path,
        uid=uid_value,
        gid=gid_value,
    )
    directory_path.chmod(WORKSPACE_MODE)


def create_runtime_media(
    service_user: str,
    repository_root: str | Path,
) -> None:
    """Create the runtime media tree for the Betabox service account."""

    service_user_value = _validate_string(
        service_user,
        name="service_user",
    )
    repository_path = _validate_path(
        repository_root,
        name="repository_root",
    )

    try:
        account = pwd.getpwnam(service_user_value)
    except KeyError as exc:
        raise RuntimeError(
            f"Linux account does not exist: {service_user_value}"
        ) from exc

    home = Path(account.pw_dir)
    media = home / "media"
    sounds = media / "sounds"

    for directory in (
        media,
        media / "pictures",
        media / "videos",
        sounds,
    ):
        ensure_directory(
            directory,
            uid=account.pw_uid,
            gid=account.pw_gid,
        )

    assets = repository_path / "deployment" / "assets" / "sounds"

    install_directory(
        assets,
        sounds,
        uid=account.pw_uid,
        gid=account.pw_gid,
    )


def create_workspace(
    account: ProvisionedAccount,
) -> None:
    """Create the workspace for a managed account."""
    if not account.home.is_dir():
        raise RuntimeError(f"Account home directory does not exist: {account.home}")

    uid, _ = account_ids(account.username)
    gid = group_id(BETABOX_SHARED_GROUP)

    for directory in workspace_directories(account):
        ensure_directory(
            directory,
            uid=uid,
            gid=gid,
        )


def _set_ownership(
    path: Path,
    *,
    uid: int,
    gid: int,
) -> None:
    os.chown(
        path,
        uid,
        gid,
        follow_symlinks=False,
    )


def set_ownership_recursive(
    path: str | Path,
    *,
    uid: int,
    gid: int,
) -> None:
    """Set ownership on a path and its contents."""

    target = _validate_path(
        path,
        name="path",
    )
    uid_value = _validate_id(
        uid,
        name="uid",
    )
    gid_value = _validate_id(
        gid,
        name="gid",
    )

    if not target.exists() and not target.is_symlink():
        raise FileNotFoundError(f"Ownership target does not exist: {target}")

    _set_ownership(
        target,
        uid=uid_value,
        gid=gid_value,
    )

    if not target.is_dir() or target.is_symlink():
        return

    for child in target.rglob("*"):
        _set_ownership(
            child,
            uid=uid_value,
            gid=gid_value,
        )


def install_directory(
    source: str | Path,
    destination: str | Path,
    *,
    uid: int,
    gid: int,
) -> None:
    """Copy assets without overwriting existing files."""

    source_path = _validate_path(
        source,
        name="source",
    )
    destination_path = _validate_path(
        destination,
        name="destination",
    )
    uid_value = _validate_id(
        uid,
        name="uid",
    )
    gid_value = _validate_id(
        gid,
        name="gid",
    )

    if not source_path.is_dir():
        raise FileNotFoundError(f"Asset source directory does not exist: {source_path}")

    destination_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not destination_path.is_dir():
        raise NotADirectoryError(
            f"Asset destination is not a directory: {destination_path}"
        )

    _set_ownership(
        destination_path,
        uid=uid_value,
        gid=gid_value,
    )

    for item in source_path.iterdir():
        if item.is_symlink():
            raise ValueError(f"Asset source contains a symbolic link: {item}")

        target = destination_path / item.name

        if target.exists() or target.is_symlink():
            set_ownership_recursive(
                target,
                uid=uid_value,
                gid=gid_value,
            )
            continue

        if item.is_dir():
            _ = shutil.copytree(
                item,
                target,
            )
        elif item.is_file():
            _ = shutil.copy2(
                item,
                target,
            )
        else:
            raise ValueError(f"Unsupported asset type: {item}")

        set_ownership_recursive(
            target,
            uid=uid_value,
            gid=gid_value,
        )


def populate_media(
    repository_root: str | Path,
    *,
    accounts: Iterable[ProvisionedAccount] = BETABOX_ACCOUNTS,
) -> None:
    """Install starter media for managed accounts."""

    repository_path = _validate_path(
        repository_root,
        name="repository_root",
    )

    try:
        account_values = tuple(accounts)
    except TypeError as exc:
        raise TypeError("accounts must be iterable") from exc

    assets = repository_path / "deployment" / "assets" / "sounds"
    gid = group_id(BETABOX_SHARED_GROUP)

    for account in account_values:
        if not account.install_media:
            continue

        uid, _ = account_ids(account.username)

        install_directory(
            assets,
            account.home / "media" / "sounds",
            uid=uid,
            gid=gid,
        )
