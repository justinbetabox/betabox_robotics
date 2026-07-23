from __future__ import annotations

import os
from pathlib import Path

from .models import BETABOX_ACCOUNTS, ProvisionedAccount
from .utils import account_ids


WORKSPACE_MODE = 0o2770


def workspace_directories(
    account: ProvisionedAccount,
) -> tuple[Path, ...]:
    """Return the directories in an account workspace."""

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


def provision_workspace(
    account: ProvisionedAccount,
) -> None:
    """Provision the workspace for one account."""

    uid, gid = account_ids(
        account.username
    )

    print(
        f"Provisioning workspace: "
        f"{account.home}"
    )

    for directory in workspace_directories(
        account
    ):
        ensure_directory(
            directory,
            uid=uid,
            gid=gid,
        )


def provision_workspaces() -> None:
    """Provision all account workspaces."""

    for account in BETABOX_ACCOUNTS:
        provision_workspace(
            account
        )
