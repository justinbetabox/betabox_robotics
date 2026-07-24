from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass(slots=True, frozen=True)
class Session:
    """Launchpad browser session."""

    id: str | None
    username: str

    @classmethod
    def guest(cls) -> Session:
        """Return the anonymous guest identity."""

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

        return cls(
            id=uuid4().hex,
            username=username,
        )
