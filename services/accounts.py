from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

BETABOX_SHARED_GROUP = "betabox"


@dataclass(frozen=True)
class ProvisionedAccount:
    """Declarative configuration for a managed Betabox account."""

    username: str
    display_name: str
    group: str
    home: Path
    shell: Path

    password: str | None = None
    password_max_days: int | None = None
    supplemental_groups: tuple[str, ...] = ()

    persistent: bool = True
    install_media: bool = True


BETABOX_ACCOUNTS: tuple[ProvisionedAccount, ...] = (
    ProvisionedAccount(
        username="guest",
        display_name="Guest",
        group="guest",
        home=Path("/home/guest"),
        shell=Path("/usr/sbin/nologin"),
        supplemental_groups=(BETABOX_SHARED_GROUP,),
        persistent=False,
    ),
    ProvisionedAccount(
        username="admin",
        display_name="Administrator",
        group="admin",
        home=Path("/home/admin"),
        shell=Path("/bin/bash"),
        password="teachthefuture",  # or another default if you prefer
        password_max_days=None,
        supplemental_groups=(BETABOX_SHARED_GROUP,),
        persistent=True,
    ),
    ProvisionedAccount(
        username="student",
        display_name="Student",
        group="student",
        home=Path("/home/student"),
        shell=Path("/bin/bash"),
        password="learnbydoing",
        supplemental_groups=(BETABOX_SHARED_GROUP,),
    ),
    ProvisionedAccount(
        username="student1",
        display_name="Student 1",
        group="student1",
        home=Path("/home/student1"),
        shell=Path("/bin/bash"),
        password="learnbydoing",
        supplemental_groups=(BETABOX_SHARED_GROUP,),
    ),
    ProvisionedAccount(
        username="student2",
        display_name="Student 2",
        group="student2",
        home=Path("/home/student2"),
        shell=Path("/bin/bash"),
        password="learnbydoing",
        supplemental_groups=(BETABOX_SHARED_GROUP,),
    ),
    ProvisionedAccount(
        username="student3",
        display_name="Student 3",
        group="student3",
        home=Path("/home/student3"),
        shell=Path("/bin/bash"),
        password="learnbydoing",
        supplemental_groups=(BETABOX_SHARED_GROUP,),
    ),
)


def account_by_username(
    username: str,
) -> ProvisionedAccount:
    """Return a managed Betabox account by username."""

    for account in BETABOX_ACCOUNTS:
        if account.username == username:
            return account

    raise LookupError(f"Unknown managed Betabox account: {username}")
