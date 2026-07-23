from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from .media import provision_media
from .models import (
    BETABOX_ACCOUNTS,
    ProvisionedAccount,
)
from .workspaces import provision_workspace


REPOSITORY_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


def find_account(
    username: str,
) -> ProvisionedAccount:
    """Return a managed Betabox account."""

    for account in BETABOX_ACCOUNTS:
        if account.username == username:
            return account

    raise RuntimeError(
        f"Unknown Betabox account: {username}"
    )


def reset_workspace(
    account: ProvisionedAccount,
) -> None:
    """Remove and recreate a temporary account workspace."""

    if account.persistent:
        raise RuntimeError(
            f"Refusing to reset persistent account: "
            f"{account.username}"
        )

    if account.home != Path("/home") / account.username:
        raise RuntimeError(
            f"Refusing to reset unexpected home path: "
            f"{account.home}"
        )

    print(
        f"Resetting workspace: {account.home}"
    )

    if account.home.exists():
        for child in account.home.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()

    provision_workspace(
        account
    )


def parse_args() -> argparse.Namespace:
    """Parse reset arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Reset a temporary Betabox workspace."
        )
    )

    parser.add_argument(
        "username",
        help="Managed account to reset.",
    )

    return parser.parse_args()


def main() -> None:
    """Reset a temporary Betabox workspace."""

    if os.geteuid() != 0:
        raise SystemExit(
            "Workspace reset must run as root."
        )

    args = parse_args()
    account = find_account(
        args.username
    )

    reset_workspace(
        account
    )

    if account.install_media:
        provision_media(
            REPOSITORY_ROOT,
            accounts=(account,),
        )

    print(
        f"Workspace reset complete: "
        f"{account.username}"
    )


if __name__ == "__main__":
    main()
