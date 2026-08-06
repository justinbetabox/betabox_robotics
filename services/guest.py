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


@dataclass(frozen=True, slots=True)
class GuestWorkspaceStatus:
    """Current state of the Guest workspace."""

    account_exists: bool
    home_exists: bool
    curriculum_exists: bool
    media_exists: bool
    preferences_exist: bool

    def __post_init__(
        self,
    ) -> None:
        for name in (
            "account_exists",
            "home_exists",
            "curriculum_exists",
            "media_exists",
            "preferences_exist",
        ):
            if not isinstance(
                getattr(self, name),
                bool,
            ):
                raise TypeError(f"{name} must be a boolean")

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
    repository_root: str | Path = DEFAULT_REPOSITORY_ROOT,
) -> None:
    repository_root_value = _validate_path(
        repository_root,
        name="repository_root",
    )

    require_root()

    account = guest_account()

    create_workspace(account)

    if account.install_media:
        populate_media(
            repository_root_value,
            accounts=(account,),
        )


def reset_guest(
    *,
    repository_root: str | Path = DEFAULT_REPOSITORY_ROOT,
) -> None:
    """Reset the temporary Guest workspace."""
    repository_root_value = _validate_path(
        repository_root,
        name="repository_root",
    )
    require_root()

    account = guest_account()

    if account.persistent:
        raise RuntimeError("Refusing to reset a persistent account.")

    expected_home = Path("/home") / account.username

    if account.home != expected_home:
        raise RuntimeError(f"Refusing to reset unexpected path: {account.home}")

    if not account.home.is_dir():
        raise RuntimeError(f"Guest home directory does not exist: {account.home}")

    if account.home.is_symlink():
        raise RuntimeError("Refusing to reset a symlinked Guest home.")

    for child in account.home.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()

    provision_guest(
        repository_root=repository_root_value,
    )


def guest_status() -> GuestWorkspaceStatus:
    try:
        account = guest_account()
        account_ids(account.username)

        return GuestWorkspaceStatus(
            account_exists=True,
            home_exists=(account.home.is_dir()),
            curriculum_exists=(account.home / "curriculum").is_dir(),
            media_exists=(account.home / "media").is_dir(),
            preferences_exist=(account.home / "preferences").is_dir(),
        )

    except (
        LookupError,
        RuntimeError,
        OSError,
    ):
        return GuestWorkspaceStatus(
            account_exists=False,
            home_exists=False,
            curriculum_exists=False,
            media_exists=False,
            preferences_exist=False,
        )


def print_status(
    status: GuestWorkspaceStatus,
) -> None:
    if not isinstance(
        status,
        GuestWorkspaceStatus,
    ):
        raise TypeError("status must be a GuestWorkspaceStatus")

    print(f"Account:      {'OK' if status.account_exists else 'Missing'}")
    print(f"Home:         {'OK' if status.home_exists else 'Missing'}")
    print(f"Curriculum:   {'OK' if status.curriculum_exists else 'Missing'}")
    print(f"Media:        {'OK' if status.media_exists else 'Missing'}")
    print(f"Preferences:  {'OK' if status.preferences_exist else 'Missing'}")


def _build_parser() -> argparse.ArgumentParser:
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

    return parser


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    return _build_parser().parse_args(argv)


def main(
    argv: list[str] | None = None,
) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "status":
            status = guest_status()
            print_status(status)
            return 0 if status.ok else 1

        if args.command == "provision":
            require_root_or_elevate(
                [
                    "guest",
                    "provision",
                ]
            )
            provision_guest()
            print("Guest workspace provisioned.")
            return 0

        if args.command == "reset":
            require_root_or_elevate(
                [
                    "guest",
                    "reset",
                ]
            )
            reset_guest()
            print("Guest workspace reset.")
            return 0

    except (
        LookupError,
        PermissionError,
        RuntimeError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        print(
            f"Guest workspace operation failed: {exc}",
            file=sys.stderr,
        )
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
