from __future__ import annotations

import argparse

from betabox_robotics.services.backup import main as backup_main
from betabox_robotics.services.boot_announce import main as boot_announce_main
from betabox_robotics.services.doctor import main as doctor_main
from betabox_robotics.services.hostname import main as hostname_main
from betabox_robotics.services.install_check import main as install_check_main
from betabox_robotics.services.logs import main as logs_main
from betabox_robotics.services.monitor import main as monitor_main
from betabox_robotics.services.reset import main as reset_main
from betabox_robotics.services.restore import main as restore_main
from betabox_robotics.services.services import main as services_main
from betabox_robotics.services.snapshot import main as snapshot_main
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
    subparsers.add_parser(
        "boot-announce",
        help="Run the Betabox boot announcement readiness check",
    )
    subparsers.add_parser(
        "monitor",
        help="Run the Betabox platform monitor",
    )
    subparsers.add_parser(
        "services",
        help="Show managed Betabox systemd services",
    )
    subparsers.add_parser(
        "logs",
        help="Show Betabox service logs",
    )
    subparsers.add_parser(
        "doctor",
        help="Diagnose Betabox platform issues and suggest fixes",
    )
    subparsers.add_parser(
        "backup",
        help="Create or list Betabox backups",
    )
    subparsers.add_parser(
        "snapshot",
        help="Create or list Betabox diagnostic snapshots",
    )
    subparsers.add_parser(
        "restore",
        help="Restore user data from a Betabox backup",
    )
    subparsers.add_parser(
        "reset",
        help="Reset generated Betabox media and recreate expected folders",
    )
    subparsers.add_parser(
        "set-hostname",
        help="Set hostname from Raspberry Pi serial number",
    )

    args, extra = parser.parse_known_args()

    if args.command == "install-check":
        return install_check_main()

    if args.command == "verify":
        return verify_main()

    if args.command == "status":
        return status_main(extra)

    if args.command == "boot-announce":
        return boot_announce_main()

    if args.command == "monitor":
        return monitor_main(extra)

    if args.command == "services":
        return services_main(extra)

    if args.command == "logs":
        return logs_main(extra)

    if args.command == "doctor":
        return doctor_main(extra)

    if args.command == "backup":
        return backup_main(extra)

    if args.command == "snapshot":
        return snapshot_main(extra)

    if args.command == "restore":
        return restore_main(extra)

    if args.command == "reset":
        return reset_main(extra)

    if args.command == "set-hostname":
        return hostname_main(extra)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
