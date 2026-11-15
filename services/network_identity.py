
from __future__ import annotations

import socket

from betabox_robotics.services.command import run


def hostname() -> str:
    value = socket.gethostname().strip()

    if not value:
        raise ValueError("hostname cannot be empty")

    return value


def ip_addresses() -> tuple[str, ...]:
    result = run(
        [
            "hostname",
            "-I",
        ],
        timeout=3,
    )

    if result is None or result.returncode != 0:
        return ()

    addresses: list[str] = []

    for address in result.stdout.split():
        value = address.strip()

        if not value:
            continue

        if (
            value.startswith("127.")
            or value == "0.0.0.0"
            or value == "::"
            or value == "::1"
        ):
            continue

        if value not in addresses:
            addresses.append(value)

    return tuple(addresses)
