from __future__ import annotations

from betabox_robotics.services.command import run

from .models import NetworkInterfaceStatus
from .validation import validate_interface_name


def collect_network_interface(
    name: str,
) -> NetworkInterfaceStatus:
    """
    Collect NetworkManager status for one network interface.
    """

    interface_name = validate_interface_name(name)

    result = run(
        [
            "nmcli",
            "-t",
            "-f",
            "GENERAL.STATE,GENERAL.CONNECTION",
            "device",
            "show",
            interface_name,
        ],
        timeout=5,
    )

    if result is None:
        return NetworkInterfaceStatus(
            name=interface_name,
            available=False,
            connected=False,
            state="unknown",
            connection=None,
            error="nmcli device query failed",
        )

    if result.returncode != 0:
        message = (
            result.stderr.strip()
            or result.stdout.strip()
            or "nmcli device query failed"
        )

        return NetworkInterfaceStatus(
            name=interface_name,
            available=False,
            connected=False,
            state="unknown",
            connection=None,
            error=message,
        )

    state = "unknown"
    connection: str | None = None

    for line in result.stdout.splitlines():
        key, separator, value = line.partition(":")

        if not separator:
            continue

        key = key.strip()
        value = value.strip()

        if key == "GENERAL.STATE":
            state = value or "unknown"

        elif key == "GENERAL.CONNECTION":
            connection = None if not value or value == "--" else value

    connected = state.startswith("100")

    return NetworkInterfaceStatus(
        name=interface_name,
        available=True,
        connected=connected,
        state=state,
        connection=connection,
    )
