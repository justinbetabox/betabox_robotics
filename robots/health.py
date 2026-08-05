from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _validate_string(
    value: object,
    *,
    name: str,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")

    result = value.strip()

    if not allow_empty and not result:
        raise ValueError(f"{name} cannot be empty")

    return result


def _validate_bool(
    value: object,
    *,
    name: str,
) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a boolean")

    return value


@dataclass(
    frozen=True,
    slots=True,
)
class HealthCheck:
    name: str
    ok: bool
    message: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "name",
            _validate_string(
                self.name,
                name="name",
            ),
        )
        object.__setattr__(
            self,
            "ok",
            _validate_bool(
                self.ok,
                name="ok",
            ),
        )
        object.__setattr__(
            self,
            "message",
            _validate_string(
                self.message,
                name="message",
                allow_empty=True,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "message": self.message,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class RobotHealth:
    ok: bool
    checks: tuple[HealthCheck, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "ok",
            _validate_bool(
                self.ok,
                name="ok",
            ),
        )

        if not isinstance(
            self.checks,
            tuple,
        ):
            raise TypeError("checks must be a tuple")

        for check in self.checks:
            if not isinstance(
                check,
                HealthCheck,
            ):
                raise TypeError("checks must contain only HealthCheck instances")

    @property
    def messages(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            check.message for check in self.checks if not check.ok and check.message
        )

    @property
    def failed_checks(
        self,
    ) -> tuple[HealthCheck, ...]:
        return tuple(check for check in self.checks if not check.ok)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": [check.to_dict() for check in self.checks],
        }
