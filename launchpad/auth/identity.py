from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


def _validate_string(
    value: object,
    *,
    name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(f"{name} must be a string")

    result = value.strip()

    if not result:
        raise ValueError(f"{name} cannot be empty")

    return result


class Role(StrEnum):
    """Launchpad user roles."""

    GUEST = "guest"
    STUDENT = "student"
    TEACHER = "teacher"


@dataclass(
    slots=True,
    frozen=True,
)
class Identity:
    """Current Launchpad user."""

    username: str
    display_name: str
    role: Role
    authenticated: bool

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "username",
            _validate_string(
                self.username,
                name="username",
            ),
        )
        object.__setattr__(
            self,
            "display_name",
            _validate_string(
                self.display_name,
                name="display_name",
            ),
        )

        if not isinstance(
            self.role,
            Role,
        ):
            raise TypeError("role must be a Role")

        if not isinstance(
            self.authenticated,
            bool,
        ):
            raise TypeError("authenticated must be a boolean")

    @property
    def guest(
        self,
    ) -> bool:
        return self.role is Role.GUEST

    @property
    def student(
        self,
    ) -> bool:
        return self.role is Role.STUDENT

    @property
    def teacher(
        self,
    ) -> bool:
        return self.role is Role.TEACHER
