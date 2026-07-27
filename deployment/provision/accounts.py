from __future__ import annotations

import grp
import pwd
import subprocess
from pathlib import Path

from betabox_robotics.services.accounts import (
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


def group_exists(group: str) -> bool:
    """Return whether a Linux group exists."""

    try:
        grp.getgrnam(group)
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


def ensure_account_group(
    account: ProvisionedAccount,
) -> None:
    """Ensure a managed account group exists."""

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


def update_account(
    account: ProvisionedAccount,
) -> None:
    """Apply the expected home and shell to an existing account."""

    entry = pwd.getpwnam(account.username)

    command = [
        "usermod",
    ]

    changed = False

    if Path(entry.pw_dir) != account.home:
        command.extend(
            [
                "--home",
                str(account.home),
                "--move-home",
            ]
        )
        changed = True

    if Path(entry.pw_shell) != account.shell:
        command.extend(
            [
                "--shell",
                str(account.shell),
            ]
        )
        changed = True

    if not changed:
        print(f"Account configuration is current: {account.username}")
        return

    command.append(account.username)

    print(f"Updating account configuration: {account.username}")

    run_command(*command)


def ensure_account(
    account: ProvisionedAccount,
    *,
    service_user: str | None = None,
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
    ensure_service_user_access(
        account,
        service_user,
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


def ensure_group_membership(
    *,
    username: str,
    group: str,
) -> None:
    """Ensure a user belongs to a supplementary group."""

    try:
        user = pwd.getpwnam(username)
    except KeyError as exc:
        raise RuntimeError(f"Service account does not exist: {username}") from exc

    try:
        group_entry = grp.getgrnam(group)
    except KeyError as exc:
        raise RuntimeError(f"Required group does not exist: {group}") from exc

    if user.pw_gid == group_entry.gr_gid or username in group_members(group):
        print(f"{username} already has access to group {group}")
        return

    print(f"Adding {username} to group {group}")

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
        ensure_account(
            account,
            service_user=service_user,
        )


def ensure_account_password(
    account: ProvisionedAccount,
) -> None:
    """Set the declared password for a managed account."""

    if account.password is None:
        return

    print(f"Setting account password: {account.username}")

    subprocess.run(
        ["chpasswd"],
        input=(f"{account.username}:{account.password}\n"),
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


def user_is_group_member(
    username: str,
    group: str,
) -> bool:
    """Return whether a user belongs to a Linux group."""

    account = pwd.getpwnam(username)
    group_entry = grp.getgrnam(group)

    if account.pw_gid == group_entry.gr_gid:
        return True

    return username in group_entry.gr_mem


def ensure_group_member(
    username: str,
    group: str,
) -> None:
    """Ensure a user belongs to a Linux group."""

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


def ensure_supplemental_groups(
    account: ProvisionedAccount,
) -> None:
    """Ensure declared supplemental group memberships."""

    for group in account.supplemental_groups:
        ensure_group_member(
            account.username,
            group,
        )


def ensure_service_user_access(
    account: ProvisionedAccount,
    service_user: str | None,
) -> None:
    """Give the service user access to a persistent workspace."""

    if service_user is None:
        return

    if not account.persistent:
        return

    if service_user == account.username:
        return

    ensure_group_member(
        service_user,
        account.group,
    )
