from __future__ import annotations

import argparse
from collections.abc import Callable

from betabox_robotics.launchpad.app import (
    main as launchpad_main,
)
from betabox_robotics.services.backup import (
    main as backup_main,
)
from betabox_robotics.services.boot_announce import (
    main as boot_announce_main,
)
from betabox_robotics.services.doctor import (
    main as doctor_main,
)
from betabox_robotics.services.events import (
    main as events_main,
)
from betabox_robotics.services.guest import (
    main as guest_main,
)
from betabox_robotics.services.hostname import (
    main as hostname_main,
)
from betabox_robotics.services.install_check import (
    main as install_check_main,
)
from betabox_robotics.services.logs import (
    main as logs_main,
)
from betabox_robotics.services.monitor import (
    main as monitor_main,
)
from betabox_robotics.services.reset import (
    main as reset_main,
)
from betabox_robotics.services.restore import (
    main as restore_main,
)
from betabox_robotics.services.services import (
    main as services_main,
)
from betabox_robotics.services.snapshot import (
    main as snapshot_main,
)
from betabox_robotics.services.status import (
    main as status_main,
)
from betabox_robotics.services.verify import (
    main as verify_main,
)
from betabox_robotics.services.video import (
    main as video_main,
)
from betabox_robotics.services.wifi_fallback import (
    main as wifi_fallback_main,
)

CommandHandler = Callable[
    [list[str] | None],
    int,
]


def _without_args(
    handler: Callable[[], int],
) -> CommandHandler:
    def wrapped(
        argv: list[str] | None = None,
    ) -> int:
        if argv:
            raise ValueError("command does not accept arguments")

        return handler()

    return wrapped


COMMANDS: dict[
    str,
    tuple[
        str,
        CommandHandler,
    ],
] = {
    "install-check": (
        "Run installation checks that do not require rebooted hardware",
        install_check_main,
    ),
    "verify": (
        "Run full Betabox hardware verification checks",
        _without_args(verify_main),
    ),
    "status": (
        "Show current Betabox platform status",
        status_main,
    ),
    "boot-announce": (
        "Run the Betabox boot announcement readiness check",
        _without_args(boot_announce_main),
    ),
    "monitor": (
        "Run the Betabox platform monitor",
        monitor_main,
    ),
    "services": (
        "Show managed Betabox systemd services",
        services_main,
    ),
    "events": (
        "Show Betabox event logs",
        events_main,
    ),
    "logs": (
        "Show Betabox service logs",
        logs_main,
    ),
    "doctor": (
        "Diagnose Betabox platform issues and suggest fixes",
        doctor_main,
    ),
    "backup": (
        "Create or list Betabox backups",
        backup_main,
    ),
    "snapshot": (
        "Create or list Betabox diagnostic snapshots",
        snapshot_main,
    ),
    "restore": (
        "Restore user data from a Betabox backup",
        restore_main,
    ),
    "reset": (
        "Reset generated Betabox media and recreate expected folders",
        reset_main,
    ),
    "guest": (
        "Manage the Betabox Guest workspace",
        guest_main,
    ),
    "set-hostname": (
        "Set hostname from Raspberry Pi serial number",
        hostname_main,
    ),
    "wifi-fallback": (
        "Start fallback AP if Ethernet and Wi-Fi are unavailable",
        wifi_fallback_main,
    ),
    "video": (
        "Run the Betabox video streaming service",
        video_main,
    ),
    "launchpad": (
        "Run the Betabox Launchpad web interface",
        launchpad_main,
    ),
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="betabox")

    subparsers = parser.add_subparsers(dest="command")

    for name, (
        help_text,
        _,
    ) in COMMANDS.items():
        _ = subparsers.add_parser(
            name,
            help=help_text,
            add_help=False,
        )

    return parser


def parse_args(
    argv: list[str] | None = None,
) -> tuple[
    argparse.Namespace,
    list[str],
]:
    return _build_parser().parse_known_args(argv)


def main(
    argv: list[str] | None = None,
) -> int:
    parser = _build_parser()
    args, extra = parser.parse_known_args(argv)

    command_name = getattr(
        args,
        "command",
        None,
    )

    if not isinstance(command_name, str):
        parser.print_help()
        return 1

    command = COMMANDS.get(command_name)

    if command is None:
        parser.print_help()
        return 1

    _, handler = command

    try:
        return handler(extra)
    except (
        TypeError,
        ValueError,
    ) as exc:
        print(f"betabox {command_name} failed: {exc}")
        return 1


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
