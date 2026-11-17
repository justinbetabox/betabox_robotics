from __future__ import annotations

import argparse
import getpass
import os
import re
import subprocess
from pathlib import Path
import stat

from .accounts import CREDENTIAL_PENDING_DIR

STUDENT_ACCOUNTS = (
    "student",
    "student1",
    "student2",
    "student3",
)

ACCOUNT_GROUPS = {
    "admin": ("admin",),
    "students": STUDENT_ACCOUNTS,
    "guest": ("guest",),
}

VALID_USERNAME = re.compile(r"[a-z_][a-z0-9_-]*\Z")


def prompt_password(label: str) -> str:
    """Prompt securely for a new password."""

    while True:
        password = getpass.getpass(
            f"New {label} password: "
        )

        if not password:
            print("Password cannot be empty.")
            continue

        if any(character in password for character in "\r\n\x00"):
            print("Password contains unsupported characters.")
            continue

        confirmation = getpass.getpass(
            f"Confirm {label} password: "
        )

        if password != confirmation:
            print("Passwords do not match.")
            continue

        return password


def set_passwords(
    usernames: tuple[str, ...],
    password: str,
) -> None:
    """Set passwords for a fixed group of managed accounts."""

    allowed_groups = (
        frozenset(("admin",)),
        frozenset(STUDENT_ACCOUNTS),
        frozenset(("guest",)),
    )

    requested = frozenset(usernames)

    if (
        not usernames
        or len(requested) != len(usernames)
        or not any(requested <= group for group in allowed_groups)
    ):
        raise ValueError("Unsupported account group")

    if not password:
        raise ValueError("Password cannot be empty")

    if any(character in password for character in "\r\n\x00"):
        raise ValueError("Password contains unsupported characters")

    for username in usernames:
        if not VALID_USERNAME.fullmatch(username):
            raise ValueError("Invalid username")

    payload = "".join(
        f"{username}:{password}\n"
        for username in usernames
    )

    subprocess.run(
        ["/usr/sbin/chpasswd"],
        input=payload,
        text=True,
        check=True,
    )


def configure_credentials(group: str) -> None:
    """Interactively configure a managed account group."""

    if os.geteuid() != 0:
        raise PermissionError(
            "Credential setup requires root privileges."
        )

    if group not in ACCOUNT_GROUPS:
        raise ValueError("Unknown account group")

    usernames = ACCOUNT_GROUPS[group]

    password = prompt_password(group)

    set_passwords(usernames, password)

    print(f"Password configuration complete: {group}")

def password_needs_initialization(username: str) -> bool:
    """Return True only for accounts with an unset password."""

    result = subprocess.run(
        ["/usr/bin/passwd", "-S", username],
        capture_output=True,
        text=True,
        check=True,
    )

    fields = result.stdout.split()

    if len(fields) < 2:
        raise RuntimeError(
            f"Unexpected password status for {username}"
        )

    status = fields[1]

    if status == "NP":
        return True

    if status in ("P", "L"):
        return False

    raise RuntimeError(
        f"Unknown password status for {username}: {status}"
    )

def credentials_pending(username: str) -> bool:
    """Check for a trusted, pending password initialization."""

    if username not in ("admin", *STUDENT_ACCOUNTS):
        raise ValueError("Unsupported credential account")

    marker = CREDENTIAL_PENDING_DIR / username

    try:
        directory_info = CREDENTIAL_PENDING_DIR.lstat()
    except FileNotFoundError:
        return False

    if (
        not stat.S_ISDIR(directory_info.st_mode)
        or directory_info.st_uid != 0
        or directory_info.st_mode & 0o077
    ):
        raise RuntimeError("Unsafe credential state directory")

    try:
        marker_info = marker.lstat()
    except FileNotFoundError:
        return False

    if (
        not stat.S_ISREG(marker_info.st_mode)
        or marker_info.st_uid != 0
        or marker_info.st_mode & 0o077
    ):
        raise RuntimeError(f"Unsafe credential marker: {username}")

    # An interrupted installer may have set the password
    # successfully before clearing its marker.
    if not password_needs_initialization(username):
        result = subprocess.run(
            ["/usr/bin/passwd", "-S", username],
            capture_output=True,
            text=True,
            check=True,
        )

        if result.stdout.split()[1] == "P":
            clear_credentials_pending(username)
            return False

    return True


def clear_credentials_pending(username: str) -> None:
    """Clear the marker after successfully setting a password."""

    (CREDENTIAL_PENDING_DIR / username).unlink(
        missing_ok=True,
    )

def initialize_credentials() -> None:
    """Initialize missing credentials without resetting existing passwords."""

    if os.geteuid() != 0:
        raise RuntimeError("Credential setup requires root privileges.")

    # Administrator
    if credentials_pending("admin") or password_needs_initialization("admin"):
        password = prompt_password("Administrator")
        set_passwords(("admin",), password)
        clear_credentials_pending("admin")
    else:
        print("Administrator password already configured.")

    # Students
    students = tuple(
        username
        for username in STUDENT_ACCOUNTS
        if credentials_pending(username)
        or password_needs_initialization(username)
    )

    if students:
        password = prompt_password("Students")
        set_passwords(students, password)

        for username in students:
            clear_credentials_pending(username)
    else:
        print("Student passwords already configured.")

    # Guest remains locked and is managed separately.
    print("Guest password setup skipped.")

    print("Credential initialization complete.")

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Configure Betabox account passwords."
    )

    parser.add_argument(
        "group",
        choices=tuple(ACCOUNT_GROUPS),
        help="Account group to configure",
    )

    arguments = parser.parse_args()

    configure_credentials(arguments.group)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
