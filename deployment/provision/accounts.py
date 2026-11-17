from __future__ import annotations

import grp
import pwd
import subprocess
from pathlib import Path
import os
import stat

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

CREDENTIAL_PENDING_DIR = Path(
    "/var/lib/betabox/credentials-pending"
)

CREDENTIAL_ACCOUNTS = frozenset(
    ("admin", "student", "student1", "student2", "student3")
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

def mark_credentials_pending(username: str) -> None:
    """Record that a new account needs password initialization."""

    if username not in CREDENTIAL_ACCOUNTS:
        return

    parent = CREDENTIAL_PENDING_DIR.parent

    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    CREDENTIAL_PENDING_DIR.mkdir(exist_ok=True, mode=0o700)

    for directory in (parent, CREDENTIAL_PENDING_DIR):
        info = directory.lstat()

        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != 0
            or info.st_mode & 0o077
        ):
            raise RuntimeError(
                f"Unsafe credential directory: {directory}"
            )

    marker = CREDENTIAL_PENDING_DIR / username

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC

    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    try:
        fd = os.open(marker, flags, 0o600)
    except FileExistsError:
        info = marker.lstat()

        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != 0
            or info.st_mode & 0o077
        ):
            raise RuntimeError(
                f"Unsafe credential marker: {username}"
            )

        return

    os.close(fd)

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
) -> bool:
    """Create or reconcile an account.

    Return True only when the account was newly created.
    """

    ensure_account_group(account)

    created = not account_exists(account.username)

    if created:
        mark_credentials_pending(account.username)
        create_account(account)
    else:
        print(f"Account already exists: {account.username}")
        reconcile_account(account)

    ensure_supplemental_groups(account)

    return created


def provision_accounts(
    *,
    service_user: str,
) -> tuple[str, ...]:
    """Provision accounts and return newly created usernames."""

    ensure_shared_group()

    for group in SERVICE_USER_GROUPS:
        ensure_group_member(service_user, group)

    created_accounts: list[str] = []

    for account in BETABOX_ACCOUNTS:
        if ensure_account(account):
            created_accounts.append(account.username)

        ensure_group_member(
            service_user,
            account.group,
        )

    return tuple(created_accounts)
