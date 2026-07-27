from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from betabox_robotics.services.accounts import (
    ProvisionedAccount,
    account_by_username,
)
from betabox_robotics.services.privileges import (
    require_root_or_elevate,
)
from betabox_robotics.services.workspace import (
    account_ids,
    create_workspace,
    populate_media,
)

DEFAULT_REPOSITORY_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class GuestWorkspaceStatus:
    """Current state of the Guest workspace."""

    account_exists: bool
    home_exists: bool
    curriculum_exists: bool
    media_exists: bool
    preferences_exist: bool

    @property
    def ok(self) -> bool:
        return all(
            (
                self.account_exists,
                self.home_exists,
                self.curriculum_exists,
                self.media_exists,
                self.preferences_exist,
            )
        )


def guest_account() -> ProvisionedAccount:
    """Return the managed Guest account."""

    return account_by_username("guest")


def require_root() -> None:
    """Require root privileges for Guest modification."""

    if os.geteuid() != 0:
        raise PermissionError("Guest workspace management requires root.")


def provision_guest(
    *,
    repository_root: Path = DEFAULT_REPOSITORY_ROOT,
) -> None:
    """Create and populate the Guest workspace."""

    require_root()

    account = guest_account()

    create_workspace(account)

    if account.install_media:
        populate_media(
            repository_root,
            accounts=(account,),
        )


def reset_guest(
    *,
    repository_root: Path = DEFAULT_REPOSITORY_ROOT,
) -> None:
    """Reset the temporary Guest workspace."""

    require_root()

    account = guest_account()

    if account.persistent:
        raise RuntimeError("Refusing to reset a persistent account.")

    expected_home = Path("/home") / account.username

    if account.home != expected_home:
        raise RuntimeError(f"Refusing to reset unexpected path: {account.home}")

    if not account.home.is_dir():
        raise RuntimeError(f"Guest home directory does not exist: {account.home}")

    for child in account.home.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()

    provision_guest(
        repository_root=repository_root,
    )


def guest_status() -> GuestWorkspaceStatus:
    """Inspect the Guest account and workspace."""

    try:
        account = guest_account()
        account_ids(account.username)
        account_exists = True
    except (LookupError, RuntimeError):
        return GuestWorkspaceStatus(
            account_exists=False,
            home_exists=False,
            curriculum_exists=False,
            media_exists=False,
            preferences_exist=False,
        )

    return GuestWorkspaceStatus(
        account_exists=account_exists,
        home_exists=account.home.is_dir(),
        curriculum_exists=(account.home / "curriculum").is_dir(),
        media_exists=(account.home / "media").is_dir(),
        preferences_exist=(account.home / "preferences").is_dir(),
    )


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        prog="betabox guest",
    )

    subparsers = parser.add_subparsers(
        dest="command",
    )

    subparsers.add_parser(
        "status",
        help="Show Guest workspace status",
    )

    subparsers.add_parser(
        "provision",
        help="Create the Guest workspace",
    )

    subparsers.add_parser(
        "reset",
        help="Reset the Guest workspace",
    )

    args = parser.parse_args(argv)

    try:
        if args.command == "status":
            status = guest_status()

            print(f"Account:      {'OK' if status.account_exists else 'Missing'}")
            print(f"Home:         {'OK' if status.home_exists else 'Missing'}")
            print(f"Curriculum:   {'OK' if status.curriculum_exists else 'Missing'}")
            print(f"Media:        {'OK' if status.media_exists else 'Missing'}")
            print(f"Preferences:  {'OK' if status.preferences_exist else 'Missing'}")

            return 0 if status.ok else 1

        if args.command == "provision":
            require_root_or_elevate(
                ["guest", "provision"],
            )

            provision_guest()

            print("Guest workspace provisioned.")

            return 0

        if args.command == "reset":
            require_root_or_elevate(
                ["guest", "reset"],
            )

            reset_guest()

            print("Guest workspace reset.")

            return 0

    except Exception as exc:
        print(
            f"Guest workspace operation failed: {exc}",
            file=sys.stderr,
        )
        return 1

    parser.print_help()
    return 1
