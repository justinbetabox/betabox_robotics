from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


def _validate_username(
    value: object,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError("username must be a string")

    result = value.strip()

    if not result:
        raise ValueError("username cannot be empty")

    return result


def _validate_session_id(
    value: object,
) -> str | None:
    if value is None:
        return None

    if not isinstance(
        value,
        str,
    ):
        raise TypeError("id must be a string or None")

    result = value.strip()

    if not result:
        raise ValueError("id cannot be empty")

    return result


@dataclass(
    slots=True,
    frozen=True,
)
class Session:
    """Launchpad browser session."""

    id: str | None
    username: str

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "id",
            _validate_session_id(self.id),
        )
        object.__setattr__(
            self,
            "username",
            _validate_username(self.username),
        )

    @property
    def guest_session(
        self,
    ) -> bool:
        return self.id is None and self.username == "guest"

    @classmethod
    def guest(
        cls,
    ) -> Session:
        """Return the anonymous guest session."""

        return cls(
            id=None,
            username="guest",
        )

    @classmethod
    def for_username(
        cls,
        username: str,
    ) -> Session:
        """Create a stored session for a managed account."""

        username_value = _validate_username(username)

        if username_value == "guest":
            raise ValueError("guest sessions must use Session.guest()")

        return cls(
            id=uuid4().hex,
            username=username_value,
        )
