from __future__ import annotations

import argparse

from betabox_robotics.services.verify import main as verify_main


def main() -> int:
    parser = argparse.ArgumentParser(prog="betabox")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("verify", help="Run Betabox platform verification checks")

    args = parser.parse_args()

    if args.command == "verify":
        return verify_main()

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
