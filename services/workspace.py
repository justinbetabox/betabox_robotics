from __future__ import annotations

import os
import pwd
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


WORKSPACE_MODE = 0o2770


@dataclass(frozen=True, slots=True)
class ProvisionedAccount:
    """Description of a Betabox-managed Linux account."""

    username: str
    display_name: str
    group: str
    home: Path
    shell: Path = Path("/usr/sbin/nologin")
    persistent: bool = True
    install_media: bool = True


BETABOX_ACCOUNTS: tuple[
    ProvisionedAccount,
    ...
] = (
    ProvisionedAccount(
        username="guest",
        display_name="Guest",
        group="guest",
        home=Path("/home/guest"),
        persistent=False,
    ),
)


def account_by_username(
    username: str,
) -> ProvisionedAccount:
    """Return a managed Betabox account."""

    for account in BETABOX_ACCOUNTS:
        if account.username == username:
            return account

    raise LookupError(
        f"Unknown Betabox account: {username}"
    )


def account_ids(
    username: str,
) -> tuple[int, int]:
    """Return the UID and primary GID for an account."""

    try:
        account = pwd.getpwnam(username)
    except KeyError as exc:
        raise RuntimeError(
            f"Linux account does not exist: {username}"
        ) from exc

    return account.pw_uid, account.pw_gid


def workspace_directories(
    account: ProvisionedAccount,
) -> tuple[Path, ...]:
    """Return all directories in an account workspace."""

    media = account.home / "media"

    return (
        account.home,
        account.home / "curriculum",
        media,
        media / "pictures",
        media / "videos",
        media / "sounds",
        account.home / "preferences",
    )


def ensure_directory(
    directory: Path,
    *,
    uid: int,
    gid: int,
) -> None:
    """Create and configure one workspace directory."""

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    os.chown(
        directory,
        uid,
        gid,
    )

    directory.chmod(
        WORKSPACE_MODE
    )


def create_workspace(
    account: ProvisionedAccount,
) -> None:
    """Create the workspace for a managed account."""

    uid, gid = account_ids(
        account.username
    )

    for directory in workspace_directories(
        account
    ):
        ensure_directory(
            directory,
            uid=uid,
            gid=gid,
        )


def set_ownership_recursive(
    path: Path,
    *,
    uid: int,
    gid: int,
) -> None:
    """Set ownership on a path and its contents."""

    os.chown(
        path,
        uid,
        gid,
    )

    if not path.is_dir():
        return

    for child in path.rglob("*"):
        os.chown(
            child,
            uid,
            gid,
        )


def install_directory(
    source: Path,
    destination: Path,
    *,
    uid: int,
    gid: int,
) -> None:
    """Copy assets without overwriting existing files."""

    if not source.exists():
        raise FileNotFoundError(
            f"Asset source does not exist: {source}"
        )

    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    os.chown(
        destination,
        uid,
        gid,
    )

    for item in source.iterdir():
        target = destination / item.name

        if target.exists():
            set_ownership_recursive(
                target,
                uid=uid,
                gid=gid,
            )
            continue

        if item.is_dir():
            shutil.copytree(
                item,
                target,
            )
        else:
            shutil.copy2(
                item,
                target,
            )

        set_ownership_recursive(
            target,
            uid=uid,
            gid=gid,
        )


def populate_media(
    repository_root: Path,
    *,
    accounts: Iterable[
        ProvisionedAccount
    ] = BETABOX_ACCOUNTS,
) -> None:
    """Install starter media for managed accounts."""

    assets = (
        repository_root
        / "deployment"
        / "assets"
        / "sounds"
    )

    for account in accounts:
        if not account.install_media:
            continue

        uid, gid = account_ids(
            account.username
        )

        install_directory(
            assets,
            account.home
            / "media"
            / "sounds",
            uid=uid,
            gid=gid,
        )
