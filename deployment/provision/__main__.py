from __future__ import annotations

import argparse
import os
from pathlib import Path

from betabox_robotics.services.accounts import (
    BETABOX_ACCOUNTS,
)
from betabox_robotics.services.workspace import (
    create_runtime_media,
    create_workspace,
    populate_media,
)

from .accounts import provision_accounts

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    """Parse provisioning command-line arguments."""

    parser = argparse.ArgumentParser(
        description=("Provision Betabox accounts and workspaces.")
    )

    parser.add_argument(
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


def main() -> None:
    """Provision the installed Betabox platform."""

    args = parse_args()

    require_root()

    print("Provisioning Betabox accounts...")

    provision_accounts(
        service_user=args.service_user,
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
        args.service_user,
        REPOSITORY_ROOT,
    )

    print("Betabox provisioning complete.")


if __name__ == "__main__":
    main()
