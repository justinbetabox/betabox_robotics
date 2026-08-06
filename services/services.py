from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
    ServiceCategory,
    ServiceStartup,
)
from betabox_robotics.services.command import run
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


def _validate_config(
    value: object,
) -> PlatformConfig:
    if not isinstance(
        value,
        PlatformConfig,
    ):
        raise TypeError("config must be a PlatformConfig")

    return value


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


def _validate_properties(
    value: object,
) -> dict[str, str]:
    if not isinstance(
        value,
        dict,
    ):
        raise TypeError("properties must be a dictionary")

    normalized: dict[str, str] = {}

    for key, item in value.items():
        key_value = _validate_string(
            key,
            name="property name",
        )

        if not isinstance(
            item,
            str,
        ):
            raise TypeError("property values must be strings")

        normalized[key_value] = item.strip()

    return normalized


def _validate_statuses(
    value: object,
) -> tuple[ServiceStatus, ...]:
    if not isinstance(
        value,
        tuple,
    ):
        raise TypeError("statuses must be a tuple")

    if not all(isinstance(status, ServiceStatus) for status in value):
        raise TypeError("statuses must contain only ServiceStatus values")

    return value


@dataclass(frozen=True, slots=True)
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

    def __post_init__(
        self,
    ) -> None:
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
            "display_name",
            _validate_string(
                self.display_name,
                name="display_name",
            ),
        )
        object.__setattr__(
            self,
            "description",
            _validate_string(
                self.description,
                name="description",
                allow_empty=True,
            ),
        )
        object.__setattr__(
            self,
            "unit",
            _validate_string(
                self.unit,
                name="unit",
            ),
        )

        if not isinstance(
            self.category,
            ServiceCategory,
        ):
            raise TypeError("category must be a ServiceCategory")

        if not isinstance(
            self.startup,
            ServiceStartup,
        ):
            raise TypeError("startup must be a ServiceStartup")

        if not isinstance(
            self.installed,
            bool,
        ):
            raise TypeError("installed must be a boolean")

        for name in (
            "load_state",
            "active_state",
            "sub_state",
            "enabled_state",
        ):
            object.__setattr__(
                self,
                name,
                _validate_string(
                    getattr(self, name),
                    name=name,
                ),
            )

        if not isinstance(
            self.state,
            ServiceState,
        ):
            raise TypeError("state must be a ServiceState")

        if not isinstance(
            self.health,
            ServiceHealth,
        ):
            raise TypeError("health must be a ServiceHealth")

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


def service_properties(
    unit: str,
) -> dict[str, str]:
    unit_value = _validate_string(
        unit,
        name="unit",
    )

    result = run(
        [
            "systemctl",
            "show",
            unit_value,
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

        key_value = key.strip()

        if not key_value:
            continue

        properties[key_value] = value.strip()

    return properties


def service_is_installed(
    properties: dict[str, str],
) -> bool:
    properties_value = _validate_properties(properties)

    return properties_value.get("LoadState") == "loaded"


def normalize_state(
    *,
    installed: bool,
    active_state: str,
    sub_state: str,
    result_state: str,
    startup: ServiceStartup,
) -> tuple[
    ServiceState,
    ServiceHealth,
]:
    if not isinstance(
        installed,
        bool,
    ):
        raise TypeError("installed must be a boolean")

    active_state_value = _validate_string(
        active_state,
        name="active_state",
        allow_empty=True,
    )
    sub_state_value = _validate_string(
        sub_state,
        name="sub_state",
        allow_empty=True,
    )
    result_state_value = _validate_string(
        result_state,
        name="result_state",
        allow_empty=True,
    )

    if not isinstance(
        startup,
        ServiceStartup,
    ):
        raise TypeError("startup must be a ServiceStartup")

    if not installed:
        return (
            ServiceState.NOT_INSTALLED,
            ServiceHealth.ERROR,
        )

    if (
        active_state_value == "failed"
        or sub_state_value == "failed"
        or result_state_value
        not in {
            "",
            "success",
            "done",
        }
    ):
        return (
            ServiceState.FAILED,
            ServiceHealth.ERROR,
        )

    if active_state_value == "activating":
        return (
            ServiceState.STARTING,
            ServiceHealth.WARNING,
        )

    if active_state_value == "deactivating":
        return (
            ServiceState.STOPPING,
            ServiceHealth.WARNING,
        )

    if active_state_value == "reloading":
        return (
            ServiceState.RELOADING,
            ServiceHealth.WARNING,
        )

    if active_state_value == "active":
        if sub_state_value == "running":
            return (
                ServiceState.RUNNING,
                ServiceHealth.HEALTHY,
            )

        if sub_state_value == "exited":
            if startup in {
                ServiceStartup.ONESHOT,
                ServiceStartup.CONDITIONAL,
            }:
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

    if active_state_value == "inactive":
        if startup == ServiceStartup.CONDITIONAL:
            return (
                ServiceState.WAITING,
                ServiceHealth.HEALTHY,
            )

        if startup == ServiceStartup.ONESHOT and result_state_value in {
            "",
            "success",
            "done",
        }:
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
    if not isinstance(
        managed,
        ManagedService,
    ):
        raise TypeError("managed must be a ManagedService")

    config_value = _validate_config(config)

    definition = config_value.services.get(managed.unit)

    if definition is None:
        raise ValueError(
            "managed service is not present in the "
            f"platform service registry: {managed.unit}"
        )

    properties = service_properties(definition.unit)

    load_state = properties.get(
        "LoadState",
        "unknown",
    )

    installed = service_is_installed(properties)

    missing_state = "not-installed" if not installed else "unknown"

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
) -> tuple[ServiceStatus, ...]:
    config_value = _validate_config(config)
    managed = managed_services(config_value)

    return tuple(
        collect_service(
            service,
            config_value,
        )
        for service in managed.values()
    )


def service_summary(
    statuses: tuple[ServiceStatus, ...],
) -> dict[str, int]:
    """
    Return counts suitable for CLI and Launchpad summaries.
    """
    statuses_value = _validate_statuses(statuses)

    healthy = sum(
        1 for status in statuses_value if status.health == ServiceHealth.HEALTHY
    )

    warning = sum(
        1 for status in statuses_value if status.health == ServiceHealth.WARNING
    )

    error = sum(1 for status in statuses_value if status.health == ServiceHealth.ERROR)

    unknown = sum(
        1 for status in statuses_value if status.health == ServiceHealth.UNKNOWN
    )

    return {
        "total": len(statuses_value),
        "healthy": healthy,
        "warning": warning,
        "error": error,
        "unknown": unknown,
    }


def format_service_state(
    status: ServiceStatus,
) -> str:
    if not isinstance(
        status,
        ServiceStatus,
    ):
        raise TypeError("status must be a ServiceStatus")

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

    return labels.get(
        status.state,
        "unknown",
    )


def print_human(
    statuses: tuple[ServiceStatus, ...],
) -> None:
    """
    Print the human-readable CLI service report.
    """
    statuses_value = _validate_statuses(statuses)

    summary = service_summary(statuses_value)

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

    for status in statuses_value:
        state = format_service_state(status)

        print(
            f"{status.display_name:18} "
            f"{status.unit:36} "
            f"{state:14} "
            f"{status.enabled_state}"
        )

    print()


def print_json(
    statuses: tuple[ServiceStatus, ...],
) -> None:
    """
    Print the JSON representation used by scripts and APIs.
    """
    statuses_value = _validate_statuses(statuses)

    payload = {
        "summary": service_summary(statuses_value),
        "services": [status.to_dict() for status in statuses_value],
    }

    print(
        json.dumps(
            payload,
            indent=2,
        )
    )


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Show managed Betabox service status."),
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON output.",
    )

    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
) -> int:
    args = parse_args(argv)

    try:
        statuses = collect_services(DEFAULT_PLATFORM_CONFIG)
    except (
        TypeError,
        ValueError,
        OSError,
    ) as exc:
        print(str(exc))
        return 1

    if args.json:
        print_json(statuses)
    else:
        print_human(statuses)

    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
