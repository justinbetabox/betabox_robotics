from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

BETABOX_SHARED_GROUP = "betabox"

BETABOX_HARDWARE_GROUPS: tuple[str, ...] = (
    BETABOX_SHARED_GROUP,
    "i2c",
    "gpio",
    "spi",
    "audio",
    "video",
)

_ACCOUNT_NAME_PATTERN = re.compile(r"^[a-z_][a-z0-9_-]*$")


def _validate_name(
    value: object,
    *,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    result = value.strip()

    if not result:
        raise ValueError(f"{field_name} cannot be empty")

    return result


def _validate_account_name(
    value: object,
    *,
    field_name: str,
) -> str:
    result = _validate_name(
        value,
        field_name=field_name,
    )

    if not _ACCOUNT_NAME_PATTERN.fullmatch(result):
        raise ValueError(f"{field_name} contains invalid characters")

    return result


def _validate_path(
    value: object,
    *,
    field_name: str,
) -> Path:
    if isinstance(value, bool) or not isinstance(
        value,
        str | Path,
    ):
        raise TypeError(f"{field_name} must be a string or Path")

    path = Path(value).expanduser()

    if not path.is_absolute():
        raise ValueError(f"{field_name} must be an absolute path")

    return path


def _validate_optional_password(
    value: object,
) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError("password must be a string or None")

    if not value:
        raise ValueError("password cannot be empty")

    return value


def _validate_password_max_days(
    value: object,
) -> int | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError("password_max_days must be an integer or None")

    if value < 1:
        raise ValueError("password_max_days must be at least 1")

    return value


def _validate_bool(
    value: object,
    *,
    field_name: str,
) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a boolean")

    return value


@dataclass(frozen=True, slots=True)
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

    def __post_init__(self) -> None:
        username = _validate_account_name(
            self.username,
            field_name="username",
        )
        display_name = _validate_name(
            self.display_name,
            field_name="display_name",
        )
        group = _validate_account_name(
            self.group,
            field_name="group",
        )
        home = _validate_path(
            self.home,
            field_name="home",
        )
        shell = _validate_path(
            self.shell,
            field_name="shell",
        )
        password = _validate_optional_password(self.password)
        password_max_days = _validate_password_max_days(self.password_max_days)

        if not isinstance(
            self.supplemental_groups,
            tuple,
        ):
            raise TypeError("supplemental_groups must be a tuple")

        supplemental_groups = tuple(
            _validate_account_name(
                group_name,
                field_name="supplemental group",
            )
            for group_name in self.supplemental_groups
        )

        if len(set(supplemental_groups)) != len(supplemental_groups):
            raise ValueError("supplemental_groups cannot contain duplicates")

        persistent = _validate_bool(
            self.persistent,
            field_name="persistent",
        )
        install_media = _validate_bool(
            self.install_media,
            field_name="install_media",
        )

        object.__setattr__(
            self,
            "username",
            username,
        )
        object.__setattr__(
            self,
            "display_name",
            display_name,
        )
        object.__setattr__(
            self,
            "group",
            group,
        )
        object.__setattr__(
            self,
            "home",
            home,
        )
        object.__setattr__(
            self,
            "shell",
            shell,
        )
        object.__setattr__(
            self,
            "password",
            password,
        )
        object.__setattr__(
            self,
            "password_max_days",
            password_max_days,
        )
        object.__setattr__(
            self,
            "supplemental_groups",
            supplemental_groups,
        )
        object.__setattr__(
            self,
            "persistent",
            persistent,
        )
        object.__setattr__(
            self,
            "install_media",
            install_media,
        )


BETABOX_ACCOUNTS: tuple[ProvisionedAccount, ...] = (
    ProvisionedAccount(
        username="guest",
        display_name="Guest",
        group="guest",
        home=Path("/home/guest"),
        shell=Path("/usr/sbin/nologin"),
        supplemental_groups=(BETABOX_HARDWARE_GROUPS),
        persistent=False,
    ),
    ProvisionedAccount(
        username="admin",
        display_name="Administrator",
        group="admin",
        home=Path("/home/admin"),
        shell=Path("/bin/bash"),
        supplemental_groups=(BETABOX_HARDWARE_GROUPS),
    ),
    ProvisionedAccount(
        username="student",
        display_name="Student",
        group="student",
        home=Path("/home/student"),
        shell=Path("/bin/bash"),
        supplemental_groups=(BETABOX_HARDWARE_GROUPS),
    ),
    ProvisionedAccount(
        username="student1",
        display_name="Student 1",
        group="student1",
        home=Path("/home/student1"),
        shell=Path("/bin/bash"),
        supplemental_groups=(BETABOX_HARDWARE_GROUPS),
    ),
    ProvisionedAccount(
        username="student2",
        display_name="Student 2",
        group="student2",
        home=Path("/home/student2"),
        shell=Path("/bin/bash"),
        supplemental_groups=(BETABOX_HARDWARE_GROUPS),
    ),
    ProvisionedAccount(
        username="student3",
        display_name="Student 3",
        group="student3",
        home=Path("/home/student3"),
        shell=Path("/bin/bash"),
        supplemental_groups=(BETABOX_HARDWARE_GROUPS),
    ),
)


_ACCOUNT_USERNAMES = tuple(account.username for account in BETABOX_ACCOUNTS)

if len(set(_ACCOUNT_USERNAMES)) != len(_ACCOUNT_USERNAMES):
    raise RuntimeError("BETABOX_ACCOUNTS contains duplicate usernames")


_ACCOUNTS_BY_USERNAME: dict[
    str,
    ProvisionedAccount,
] = {account.username: account for account in BETABOX_ACCOUNTS}


def account_by_username(
    username: str,
) -> ProvisionedAccount:
    """Return a managed Betabox account by username."""

    normalized = _validate_account_name(
        username,
        field_name="username",
    )

    try:
        return _ACCOUNTS_BY_USERNAME[normalized]
    except KeyError as exc:
        raise LookupError(f"Unknown managed Betabox account: {normalized}") from exc
