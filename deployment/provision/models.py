from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProvisionedAccount:
    """Description of a Betabox user account."""

    username: str
    display_name: str
    group: str
    home: Path
    shell: Path = Path("/usr/sbin/nologin")
    persistent: bool = True
    install_media: bool = True


BETABOX_ACCOUNTS: tuple[
    ProvisionedAccount,
    ...
] = (
    ProvisionedAccount(
        username="guest",
        display_name="Guest",
        group="guest",
        home=Path("/home/guest"),
        persistent=False,
    ),
)
