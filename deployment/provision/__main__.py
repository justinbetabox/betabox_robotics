from __future__ import annotations

import argparse
import os

from pathlib import Path

from .accounts import provision_accounts
from .media import provision_media
from .workspaces import provision_workspaces

REPOSITORY_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


def parse_args() -> argparse.Namespace:
    """Parse provisioning command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Provision Betabox accounts and "
            "workspaces."
        )
    )

    parser.add_argument(
        "--service-user",
        required=True,
        help=(
            "Linux user that runs Betabox "
            "services, normally pi."
        ),
    )

    return parser.parse_args()


def require_root() -> None:
    """Require provisioning to run with root privileges."""

    if os.geteuid() != 0:
        raise SystemExit(
            "Provisioning must run as root."
        )


def main() -> None:
    """Provision the installed Betabox platform."""

    args = parse_args()

    require_root()

    print("Provisioning Betabox accounts...")
    provision_accounts(
        service_user=args.service_user,
    )

    print("Provisioning Betabox workspaces...")
    provision_workspaces()

    print("Provisioning Betabox media...")
    provision_media(
        REPOSITORY_ROOT,
    )

    print("Betabox provisioning complete.")


if __name__ == "__main__":
    main()
