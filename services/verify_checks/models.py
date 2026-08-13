from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


class CheckResultData(TypedDict):
    name: str
    ok: bool
    message: str


def _validate_string(
    value: object,
    *,
    name: str,
    allow_empty: bool = False,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(f"{name} must be a string")

    result = value.strip()

    if not allow_empty and not result:
        raise ValueError(f"{name} cannot be empty")

    return result


@dataclass(frozen=True, slots=True)
class CheckResult:
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
            "message",
            _validate_string(
                self.message,
                name="message",
                allow_empty=True,
            ),
        )

    def to_dict(
        self,
    ) -> CheckResultData:
        return {
            "name": self.name,
            "ok": self.ok,
            "message": self.message,
        }
