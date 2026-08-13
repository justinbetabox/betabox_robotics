from __future__ import annotations

import argparse
import grp
import os
import pwd
from pathlib import Path
from typing import cast

from betabox_robotics.services.accounts import (
    BETABOX_ACCOUNTS,
    BETABOX_SHARED_GROUP,
)
from betabox_robotics.services.workspace import (
    create_runtime_media,
    create_workspace,
    populate_media,
)

from .accounts import provision_accounts

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

ROBOT_LOCK_PATH = Path("/tmp/betabox-robot.lock")
ROBOT_LOCK_MODE = 0o660


def parse_args() -> argparse.Namespace:
    """Parse provisioning command-line arguments."""

    parser = argparse.ArgumentParser(
        description=("Provision Betabox accounts and workspaces.")
    )

    _ = parser.add_argument(
        "--service-user",
        required=True,
        help=(
            "Linux service account that runs Betabox "
            "services and requires access to persistent "
            "student workspaces."
        ),
    )

    return parser.parse_args()


def require_root() -> None:
    """Require provisioning to run with root privileges."""

    if os.geteuid() != 0:
        raise SystemExit("Provisioning must run as root.")


def provision_robot_lock(
    *,
    service_user: str,
) -> None:
    """Create and configure the shared robot ownership lock."""

    try:
        user = pwd.getpwnam(service_user)
    except KeyError as exc:
        raise RuntimeError(f"Linux account does not exist: {service_user}") from exc

    try:
        group = grp.getgrnam(BETABOX_SHARED_GROUP)
    except KeyError as exc:
        raise RuntimeError(
            f"Linux group does not exist: {BETABOX_SHARED_GROUP}"
        ) from exc

    base_flags = os.O_RDWR | os.O_CLOEXEC

    if hasattr(os, "O_NOFOLLOW"):
        base_flags |= os.O_NOFOLLOW

    try:
        fd = os.open(
            ROBOT_LOCK_PATH,
            base_flags,
        )
    except FileNotFoundError:
        try:
            fd = os.open(
                ROBOT_LOCK_PATH,
                base_flags | os.O_CREAT | os.O_EXCL,
                ROBOT_LOCK_MODE,
            )
        except FileExistsError:
            fd = os.open(
                ROBOT_LOCK_PATH,
                base_flags,
            )

    try:
        os.fchown(
            fd,
            user.pw_uid,
            group.gr_gid,
        )
        os.fchmod(
            fd,
            ROBOT_LOCK_MODE,
        )
    finally:
        os.close(fd)

    print(
        "Robot ownership lock is configured: "
        + f"{ROBOT_LOCK_PATH} -> "
        + f"{service_user}:{BETABOX_SHARED_GROUP}"
    )


def main() -> None:
    """Provision the installed Betabox platform."""

    args = parse_args()

    try:
        service_user = cast(
            object,
            args.service_user,
        )

        if not isinstance(
            service_user,
            str,
        ):
            raise TypeError("service_user must be a string")

        service_user = service_user.strip()

        if not service_user:
            raise ValueError("service_user cannot be empty")

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise SystemExit(str(exc)) from exc

    require_root()

    print("Provisioning Betabox accounts...")

    provision_accounts(
        service_user=service_user,
    )

    provision_robot_lock(
        service_user=service_user,
    )

    print("Provisioning Betabox workspaces...")

    for account in BETABOX_ACCOUNTS:
        create_workspace(account)

    print("Provisioning Betabox media...")

    populate_media(
        REPOSITORY_ROOT,
        accounts=BETABOX_ACCOUNTS,
    )

    create_runtime_media(
        service_user,
        REPOSITORY_ROOT,
    )

    print("Betabox provisioning complete.")


if __name__ == "__main__":
    main()
