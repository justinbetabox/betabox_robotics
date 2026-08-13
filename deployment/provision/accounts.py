from __future__ import annotations

import grp
import pwd
import subprocess
from pathlib import Path

from betabox_robotics.services.accounts import (
    BETABOX_ACCOUNTS,
    BETABOX_SHARED_GROUP,
    ProvisionedAccount,
)

SERVICE_USER_GROUPS = (
    BETABOX_SHARED_GROUP,
    "i2c",
    "gpio",
    "spi",
    "audio",
    "video",
)


def run_command(
    *command: str,
) -> None:
    """Run a system command."""

    _ = subprocess.run(
        command,
        check=True,
    )


def account_exists(username: str) -> bool:
    """Return whether a Linux account exists."""

    try:
        _ = pwd.getpwnam(username)
    except KeyError:
        return False

    return True


def group_exists(group: str) -> bool:
    """Return whether a Linux group exists."""

    try:
        _ = grp.getgrnam(group)
    except KeyError:
        return False

    return True


def ensure_shared_group() -> None:
    """Ensure the shared Betabox group exists."""

    if group_exists(BETABOX_SHARED_GROUP):
        print(f"Group already exists: {BETABOX_SHARED_GROUP}")
        return

    print(f"Creating group: {BETABOX_SHARED_GROUP}")

    run_command(
        "groupadd",
        BETABOX_SHARED_GROUP,
    )


def ensure_account_group(
    account: ProvisionedAccount,
) -> None:
    """Ensure a managed account's primary group exists."""

    if group_exists(account.group):
        print(f"Group already exists: {account.group}")
        return

    print(f"Creating group: {account.group}")

    run_command(
        "groupadd",
        account.group,
    )


def create_account(
    account: ProvisionedAccount,
) -> None:
    """Create a managed Linux account."""

    print(f"Creating account: {account.username}")

    run_command(
        "useradd",
        "--create-home",
        "--home-dir",
        str(account.home),
        "--shell",
        str(account.shell),
        "--gid",
        account.group,
        account.username,
    )


def reconcile_account(
    account: ProvisionedAccount,
) -> None:
    """Apply expected settings to an existing account."""

    entry = pwd.getpwnam(account.username)
    changes: list[str] = []

    if Path(entry.pw_dir) != account.home:
        changes.extend(
            [
                "--home",
                str(account.home),
                "--move-home",
            ]
        )

    if Path(entry.pw_shell) != account.shell:
        changes.extend(
            [
                "--shell",
                str(account.shell),
            ]
        )

    expected_group = grp.getgrnam(account.group)

    if entry.pw_gid != expected_group.gr_gid:
        changes.extend(
            [
                "--gid",
                account.group,
            ]
        )

    if not changes:
        print(f"Account configuration is current: {account.username}")
        return

    print(f"Updating account configuration: {account.username}")

    run_command(
        "usermod",
        *changes,
        account.username,
    )


def user_is_group_member(
    username: str,
    group: str,
) -> bool:
    """Return whether a user belongs to a Linux group."""

    try:
        account = pwd.getpwnam(username)
    except KeyError as exc:
        raise RuntimeError(f"Linux account does not exist: {username}") from exc

    try:
        group_entry = grp.getgrnam(group)
    except KeyError as exc:
        raise RuntimeError(f"Linux group does not exist: {group}") from exc

    if account.pw_gid == group_entry.gr_gid:
        return True

    return username in group_entry.gr_mem


def ensure_group_member(
    username: str,
    group: str,
) -> None:
    """Ensure a user belongs to a supplementary group."""

    if user_is_group_member(
        username,
        group,
    ):
        print(f"Group membership is current: {username} -> {group}")
        return

    print(f"Adding group membership: {username} -> {group}")

    run_command(
        "usermod",
        "--append",
        "--groups",
        group,
        username,
    )


def ensure_account_password(
    account: ProvisionedAccount,
) -> None:
    """Set the declared password for a managed account."""

    if account.password is None:
        return

    print(f"Setting account password: {account.username}")

    _ = subprocess.run(
        ["chpasswd"],
        input=f"{account.username}:{account.password}\n",
        text=True,
        check=True,
    )


def ensure_password_policy(
    account: ProvisionedAccount,
) -> None:
    """Apply the declared password expiration policy."""

    if account.password is None:
        return

    max_days = (
        "-1" if account.password_max_days is None else str(account.password_max_days)
    )

    run_command(
        "chage",
        "--maxdays",
        max_days,
        account.username,
    )


def ensure_supplemental_groups(
    account: ProvisionedAccount,
) -> None:
    """Ensure declared supplemental group memberships."""

    for group in account.supplemental_groups:
        ensure_group_member(
            account.username,
            group,
        )


def ensure_account(
    account: ProvisionedAccount,
) -> None:
    """Ensure a managed Linux account is fully configured."""

    ensure_account_group(account)

    if not account_exists(account.username):
        create_account(account)
    else:
        print(f"Account already exists: {account.username}")
        reconcile_account(account)

    ensure_account_password(account)
    ensure_password_policy(account)
    ensure_supplemental_groups(account)


def provision_accounts(
    *,
    service_user: str,
) -> None:
    """Provision required Linux accounts and shared access."""

    ensure_shared_group()

    for group in SERVICE_USER_GROUPS:
        ensure_group_member(
            service_user,
            group,
        )

    for account in BETABOX_ACCOUNTS:
        ensure_account(account)
