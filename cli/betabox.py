from __future__ import annotations

import argparse

from betabox_robotics.services.install_check import main as install_check_main
from betabox_robotics.services.status import main as status_main
from betabox_robotics.services.verify import main as verify_main


def main() -> int:
    parser = argparse.ArgumentParser(prog="betabox")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser(
        "install-check",
        help="Run installation checks that do not require rebooted hardware",
    )
    subparsers.add_parser(
        "verify",
        help="Run full Betabox hardware verification checks",
    )
    subparsers.add_parser(
        "status",
        help="Show current Betabox platform status",
    )

    args, extra = parser.parse_known_args()

    if args.command == "install-check":
        return install_check_main()

    if args.command == "verify":
        return verify_main()

    if args.command == "status":
        return status_main(extra)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
