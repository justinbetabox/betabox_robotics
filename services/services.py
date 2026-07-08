from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass

MANAGED_SERVICES = {
    "boot-announce": "betabox-boot-announce.service",
    "monitor": "betabox-monitor.service",
    "jupyterhub": "jupyterhub.service",
    "video": "car-video-api.service",
}


@dataclass(frozen=True)
class ServiceStatus:
    name: str
    unit: str
    installed: bool
    active_state: str
    enabled_state: str


def run(command: list[str], timeout: int = 5) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception:
        return None


def unit_exists(unit: str) -> bool:
    result = run(["systemctl", "status", unit, "--no-pager"], timeout=5)

    if result is None:
        return False

    output = result.stdout + result.stderr
    return "could not be found" not in output and "not-found" not in output


def active_state(unit: str) -> str:
    result = run(["systemctl", "is-active", unit], timeout=3)

    if result is None:
        return "unknown"

    return result.stdout.strip() or "unknown"


def enabled_state(unit: str) -> str:
    result = run(["systemctl", "is-enabled", unit], timeout=3)

    if result is None:
        return "unknown"

    return result.stdout.strip() or "unknown"


def collect_services() -> list[ServiceStatus]:
    statuses: list[ServiceStatus] = []

    for name, unit in MANAGED_SERVICES.items():
        installed = unit_exists(unit)

        statuses.append(
            ServiceStatus(
                name=name,
                unit=unit,
                installed=installed,
                active_state=active_state(unit) if installed else "not-installed",
                enabled_state=enabled_state(unit) if installed else "not-installed",
            )
        )

    return statuses


def print_human(statuses: list[ServiceStatus]) -> None:
    print()
    print("Betabox Services")
    print("================")
    print()

    for status in statuses:
        print(
            f"{status.name:14} {status.unit:34} {status.active_state:12} {status.enabled_state}"
        )

    print()


def main(argv: list[str] | None = None) -> int:
    statuses = collect_services()

    if argv and "--json" in argv:
        print(json.dumps([asdict(status) for status in statuses], indent=2))
    else:
        print_human(statuses)

    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
