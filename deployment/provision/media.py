from __future__ import annotations

import os
import shutil
from pathlib import Path

from collections.abc import Iterable

from .models import (
    BETABOX_ACCOUNTS,
    ProvisionedAccount,
)
from .utils import (
    account_ids,
    set_ownership_recursive,
)


def install_directory(
    source: Path,
    destination: Path,
    *,
    uid: int,
    gid: int,
) -> None:
    """Copy default assets without overwriting existing files."""

    if not source.exists():
        print(
            f"Media source does not exist: "
            f"{source}"
        )
        return

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


def provision_media(
    repository_root: Path,
    *,
    accounts: Iterable[
        ProvisionedAccount
    ] = BETABOX_ACCOUNTS,
) -> None:
    """Install default media assets."""

    print("Provisioning media...")

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
