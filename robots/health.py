from dataclasses import dataclass


@dataclass(frozen=True)
class HealthCheck:
    name: str
    ok: bool
    message: str = ""


@dataclass(frozen=True)
class RobotHealth:
    ok: bool
    checks: list[HealthCheck]

    @property
    def messages(self) -> list[str]:
        return [
            check.message for check in self.checks if not check.ok and check.message
        ]
