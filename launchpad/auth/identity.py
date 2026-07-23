from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    """Launchpad user roles."""

    GUEST = "guest"
    STUDENT = "student"
    TEACHER = "teacher"


@dataclass(slots=True, frozen=True)
class Identity:
    """Current Launchpad user."""

    username: str
    display_name: str
    role: Role
    authenticated: bool

    @property
    def guest(self) -> bool:
        return self.role is Role.GUEST

    @property
    def student(self) -> bool:
        return self.role is Role.STUDENT

    @property
    def teacher(self) -> bool:
        return self.role is Role.TEACHER
