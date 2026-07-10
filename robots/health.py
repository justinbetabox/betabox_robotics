from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class HealthCheck:
    name: str
    ok: bool
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RobotHealth:
    ok: bool
    checks: list[HealthCheck] = field(default_factory=list)

    @property
    def messages(self) -> list[str]:
        return [
            check.message
            for check in self.checks
            if not check.ok and check.message
        ]

    @property
    def failed_checks(self) -> list[HealthCheck]:
        return [
            check
            for check in self.checks
            if not check.ok
        ]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
