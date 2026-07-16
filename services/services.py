from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
    ServiceCategory,
    ServiceStartup,
)
from betabox_robotics.services.managed import (
    ManagedService,
    managed_services,
)


class ServiceState(str, Enum):
    """
    Friendly service states exposed by the Betabox Platform.

    These states translate low-level systemd details into values that
    are meaningful to CLI and Launchpad users.
    """

    RUNNING = "running"
    COMPLETED = "completed"
    WAITING = "waiting"
    STARTING = "starting"
    STOPPING = "stopping"
    RELOADING = "reloading"
    INACTIVE = "inactive"
    FAILED = "failed"
    NOT_INSTALLED = "not-installed"
    UNKNOWN = "unknown"


class ServiceHealth(str, Enum):
    """
    Normalized health state for a managed platform service.
    """

    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ServiceStatus:
    """
    Current status of a managed Betabox systemd service.
    """

    name: str
    display_name: str
    description: str
    unit: str

    category: ServiceCategory
    startup: ServiceStartup

    installed: bool
    load_state: str
    active_state: str
    sub_state: str
    enabled_state: str

    state: ServiceState
    health: ServiceHealth

    def to_dict(self) -> dict[str, Any]:
        """
        Return a JSON-safe dictionary representation.
        """

        data = asdict(self)

        data["category"] = self.category.value
        data["startup"] = self.startup.value
        data["state"] = self.state.value
        data["health"] = self.health.value

        return data


def run(
    command: list[str],
    timeout: int = 5,
) -> subprocess.CompletedProcess[str] | None:
    """
    Run a command and return its completed result.

    Returns ``None`` if the command cannot be executed or does not
    finish before the timeout.
    """

    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (
        OSError,
        subprocess.SubprocessError,
    ):
        return None


def service_properties(
    unit: str,
) -> dict[str, str]:
    """
    Read the systemd properties needed to classify a service.

    One ``systemctl show`` call is used instead of separate status,
    active-state, and enabled-state commands.
    """

    result = run(
        [
            "systemctl",
            "show",
            unit,
            "--no-pager",
            "--property=LoadState",
            "--property=ActiveState",
            "--property=SubState",
            "--property=UnitFileState",
            "--property=Result",
        ],
        timeout=5,
    )

    if result is None:
        return {}

    properties: dict[str, str] = {}

    for line in result.stdout.splitlines():
        key, separator, value = line.partition("=")

        if not separator:
            continue

        properties[key.strip()] = value.strip()

    return properties


def service_is_installed(
    properties: dict[str, str],
) -> bool:
    """
    Return whether systemd recognizes the service unit.
    """

    return properties.get("LoadState") == "loaded"


def normalize_state(
    *,
    installed: bool,
    active_state: str,
    sub_state: str,
    result_state: str,
    startup: ServiceStartup,
) -> tuple[ServiceState, ServiceHealth]:
    """
    Convert systemd state into a friendly platform state and health.

    Continuous services are expected to remain running. One-shot
    services may finish successfully. Conditional services may remain
    inactive when their action is not currently required.
    """

    if not installed:
        return (
            ServiceState.NOT_INSTALLED,
            ServiceHealth.ERROR,
        )

    if (
        active_state == "failed"
        or sub_state == "failed"
        or result_state not in (
            "",
            "success",
            "done",
        )
    ):
        return (
            ServiceState.FAILED,
            ServiceHealth.ERROR,
        )

    if active_state == "activating":
        return (
            ServiceState.STARTING,
            ServiceHealth.WARNING,
        )

    if active_state == "deactivating":
        return (
            ServiceState.STOPPING,
            ServiceHealth.WARNING,
        )

    if active_state == "reloading":
        return (
            ServiceState.RELOADING,
            ServiceHealth.WARNING,
        )

    if active_state == "active":
        if sub_state == "running":
            return (
                ServiceState.RUNNING,
                ServiceHealth.HEALTHY,
            )

        if sub_state == "exited":
            if startup in (
                ServiceStartup.ONESHOT,
                ServiceStartup.CONDITIONAL,
            ):
                return (
                    ServiceState.COMPLETED,
                    ServiceHealth.HEALTHY,
                )

            return (
                ServiceState.INACTIVE,
                ServiceHealth.ERROR,
            )

        if startup == ServiceStartup.CONTINUOUS:
            return (
                ServiceState.RUNNING,
                ServiceHealth.HEALTHY,
            )

        return (
            ServiceState.COMPLETED,
            ServiceHealth.HEALTHY,
        )

    if active_state == "inactive":
        if startup == ServiceStartup.CONDITIONAL:
            return (
                ServiceState.WAITING,
                ServiceHealth.HEALTHY,
            )

        if (
            startup == ServiceStartup.ONESHOT
            and result_state in (
                "",
                "success",
                "done",
            )
        ):
            return (
                ServiceState.COMPLETED,
                ServiceHealth.HEALTHY,
            )

        return (
            ServiceState.INACTIVE,
            ServiceHealth.ERROR,
        )

    return (
        ServiceState.UNKNOWN,
        ServiceHealth.UNKNOWN,
    )


def collect_service(
    managed: ManagedService,
    config: PlatformConfig,
) -> ServiceStatus:
    """
    Collect the current state of one managed service.
    """

    definition = config.services.get(
        managed.unit
    )

    if definition is None:
        raise ValueError(
            "managed service is not present in the "
            f"platform service registry: {managed.unit}"
        )

    properties = service_properties(
        definition.unit
    )

    load_state = properties.get(
        "LoadState",
        "unknown",
    )

    installed = service_is_installed(
        properties
    )

    missing_state = (
        "not-installed"
        if not installed
        else "unknown"
    )

    active_state = properties.get(
        "ActiveState",
        missing_state,
    )

    sub_state = properties.get(
        "SubState",
        missing_state,
    )

    enabled_state = properties.get(
        "UnitFileState",
        missing_state,
    )

    result_state = properties.get(
        "Result",
        "",
    )

    state, health = normalize_state(
        installed=installed,
        active_state=active_state,
        sub_state=sub_state,
        result_state=result_state,
        startup=definition.startup,
    )

    return ServiceStatus(
        name=managed.name,
        display_name=definition.display_name,
        description=definition.description,
        unit=definition.unit,
        category=definition.category,
        startup=definition.startup,
        installed=installed,
        load_state=load_state,
        active_state=active_state,
        sub_state=sub_state,
        enabled_state=enabled_state,
        state=state,
        health=health,
    )


def collect_services(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> list[ServiceStatus]:
    """
    Collect status for every managed Betabox service.
    """

    managed = managed_services(
        config
    )

    return [
        collect_service(
            service,
            config,
        )
        for service in managed.values()
    ]


def service_summary(
    statuses: list[ServiceStatus],
) -> dict[str, int]:
    """
    Return counts suitable for CLI and Launchpad summaries.
    """

    healthy = sum(
        1
        for status in statuses
        if status.health == ServiceHealth.HEALTHY
    )

    warning = sum(
        1
        for status in statuses
        if status.health == ServiceHealth.WARNING
    )

    error = sum(
        1
        for status in statuses
        if status.health == ServiceHealth.ERROR
    )

    unknown = sum(
        1
        for status in statuses
        if status.health == ServiceHealth.UNKNOWN
    )

    return {
        "total": len(statuses),
        "healthy": healthy,
        "warning": warning,
        "error": error,
        "unknown": unknown,
    }


def format_service_state(
    status: ServiceStatus,
) -> str:
    """
    Return a human-readable state label.
    """

    labels = {
        ServiceState.RUNNING: "running",
        ServiceState.COMPLETED: "completed",
        ServiceState.WAITING: "waiting",
        ServiceState.STARTING: "starting",
        ServiceState.STOPPING: "stopping",
        ServiceState.RELOADING: "reloading",
        ServiceState.INACTIVE: "inactive",
        ServiceState.FAILED: "failed",
        ServiceState.NOT_INSTALLED: "not installed",
        ServiceState.UNKNOWN: "unknown",
    }

    return labels[status.state]


def print_human(
    statuses: list[ServiceStatus],
) -> None:
    """
    Print the human-readable CLI service report.
    """

    summary = service_summary(
        statuses
    )

    print()
    print("Betabox Services")
    print("================")
    print()

    print(
        f"Healthy: {summary['healthy']}  "
        f"Warning: {summary['warning']}  "
        f"Errors: {summary['error']}  "
        f"Unknown: {summary['unknown']}"
    )

    print()

    for status in statuses:
        state = format_service_state(
            status
        )

        print(
            f"{status.display_name:18} "
            f"{status.unit:36} "
            f"{state:14} "
            f"{status.enabled_state}"
        )

    print()


def print_json(
    statuses: list[ServiceStatus],
) -> None:
    """
    Print the JSON representation used by scripts and APIs.
    """

    payload = {
        "summary": service_summary(
            statuses
        ),
        "services": [
            status.to_dict()
            for status in statuses
        ],
    }

    print(
        json.dumps(
            payload,
            indent=2,
        )
    )


def main(
    argv: list[str] | None = None,
) -> int:
    config = DEFAULT_PLATFORM_CONFIG
    statuses = collect_services(
        config
    )

    if argv and "--json" in argv:
        print_json(
            statuses
        )
    else:
        print_human(
            statuses
        )

    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(
        main(
            sys.argv[1:]
        )
    )
