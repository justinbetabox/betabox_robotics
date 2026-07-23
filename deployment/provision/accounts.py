from __future__ import annotations

import grp
import pwd
import subprocess

from betabox_robotics.services.workspace import (
    BETABOX_ACCOUNTS,
    ProvisionedAccount,
)

def run_command(
    *command: str,
) -> None:
    """Run a system command."""

    subprocess.run(
        command,
        check=True,
    )

def account_exists(username: str) -> bool:
    """Return whether a Linux account exists."""

    try:
        pwd.getpwnam(username)
    except KeyError:
        return False

    return True


def group_members(username: str) -> set[str]:
    """Return the explicit members of a Linux group."""

    try:
        group = grp.getgrnam(username)
    except KeyError:
        return set()

    return set(group.gr_mem)


def create_account(account: ProvisionedAccount) -> None:
    """Create a non-interactive Linux account."""

    print(
        f"Creating account: {account.username}"
    )

    run_command(
        "useradd",
        "--create-home",
        "--home-dir",
        str(account.home),
        "--shell",
        str(account.shell),
        account.username,
    )


def ensure_account(account: ProvisionedAccount) -> None:
    """Ensure a required Linux account exists."""

    if account_exists(account.username):
        print(
            f"Account already exists: "
            f"{account.username}"
        )
        return

    create_account(account)


def ensure_group_membership(
    *,
    username: str,
    group: str,
) -> None:
    """Ensure a user belongs to a supplementary group."""

    try:
        user = pwd.getpwnam(username)
    except KeyError as exc:
        raise RuntimeError(
            f"Service account does not exist: "
            f"{username}"
        ) from exc

    try:
        group_entry = grp.getgrnam(group)
    except KeyError as exc:
        raise RuntimeError(
            f"Required group does not exist: "
            f"{group}"
        ) from exc

    if (
        user.pw_gid == group_entry.gr_gid
        or username in group_members(group)
    ):
        print(
            f"{username} already has access "
            f"to group {group}"
        )
        return

    print(
        f"Adding {username} to group {group}"
    )

    run_command(
        "usermod",
        "--append",
        "--groups",
        group,
        username,
    )


def provision_accounts(
    *,
    service_user: str,
) -> None:
    """Provision required Linux accounts."""

    for account in BETABOX_ACCOUNTS:
        ensure_account(account)

        ensure_group_membership(
            username=service_user,
            group=account.group,
        )
