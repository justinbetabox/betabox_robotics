from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, TypedDict

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
    ServiceStartup,
)
from betabox_robotics.runtime.protocol import RuntimeStatus
from betabox_robotics.services.guest import (
    GuestWorkspaceStatus,
)
from betabox_robotics.services.hardware_checks import (
    RobotHardwareStatus,
)
from betabox_robotics.services.system_checks import (
    SystemHealthStatus,
)

HealthState = Literal[
    "healthy",
    "warning",
    "error",
    "critical",
]

IssueSeverity = Literal[
    "warning",
    "error",
    "critical",
]

HEALTH_STATE_ORDER: dict[HealthState, int] = {
    "healthy": 0,
    "warning": 1,
    "error": 2,
    "critical": 3,
}


class PlatformStatusInterface(Protocol):
    @property
    def services(
        self,
    ) -> dict[str, str]: ...

    @property
    def jupyterhub_proxy_available(
        self,
    ) -> bool: ...

    @property
    def hardware(
        self,
    ) -> RobotHardwareStatus: ...

    @property
    def system_health(
        self,
    ) -> SystemHealthStatus: ...

    @property
    def guest(
        self,
    ) -> GuestWorkspaceStatus: ...

    @property
    def runtime(
        self,
    ) -> RuntimeStatus | None: ...

    @property
    def runtime_error(
        self,
    ) -> str | None: ...


class HealthIssueData(TypedDict):
    component: str
    severity: IssueSeverity
    message: str


class PlatformHealthData(TypedDict):
    state: HealthState
    issues: list[HealthIssueData]


def _validate_string(
    value: object,
    *,
    name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(f"{name} must be a string")

    result = value.strip()

    if not result:
        raise ValueError(f"{name} cannot be empty")

    return result


def _validate_config(
    value: object,
) -> PlatformConfig:
    if not isinstance(
        value,
        PlatformConfig,
    ):
        raise TypeError("config must be a PlatformConfig")

    return value


@dataclass(
    frozen=True,
    slots=True,
)
class HealthIssue:
    component: str
    severity: IssueSeverity
    message: str

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "component",
            _validate_string(
                self.component,
                name="component",
            ),
        )

        if self.severity not in {
            "warning",
            "error",
            "critical",
        }:
            raise ValueError("severity must be warning, error, or critical")

        object.__setattr__(
            self,
            "message",
            _validate_string(
                self.message,
                name="message",
            ),
        )

    def to_dict(
        self,
    ) -> HealthIssueData:
        return {
            "component": self.component,
            "severity": self.severity,
            "message": self.message,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class PlatformHealth:
    state: HealthState
    issues: tuple[HealthIssue, ...]

    def __post_init__(
        self,
    ) -> None:
        if self.state not in HEALTH_STATE_ORDER:
            raise ValueError("state must be healthy, warning, error, or critical")

        if self.state == "healthy" and self.issues:
            raise ValueError("healthy platform health cannot contain issues")

    @property
    def healthy(
        self,
    ) -> bool:
        return self.state == "healthy"

    @property
    def warning_count(
        self,
    ) -> int:
        return sum(issue.severity == "warning" for issue in self.issues)

    @property
    def error_count(
        self,
    ) -> int:
        return sum(issue.severity == "error" for issue in self.issues)

    @property
    def critical_count(
        self,
    ) -> int:
        return sum(issue.severity == "critical" for issue in self.issues)

    def to_dict(
        self,
    ) -> PlatformHealthData:
        return {
            "state": self.state,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def _health_state(
    issues: list[HealthIssue],
) -> HealthState:
    if not issues:
        return "healthy"

    state: HealthState = "healthy"

    for issue in issues:
        if issue.severity == "critical":
            issue_state: HealthState = "critical"

        elif issue.severity == "error":
            issue_state = "error"

        else:
            issue_state = "warning"

        if HEALTH_STATE_ORDER[issue_state] > HEALTH_STATE_ORDER[state]:
            state = issue_state

    return state


def _add_issue(
    issues: list[HealthIssue],
    *,
    component: str,
    severity: IssueSeverity,
    message: str,
) -> None:
    issues.append(
        HealthIssue(
            component=component,
            severity=severity,
            message=message,
        )
    )


def _runtime_healthy(
    status: PlatformStatusInterface,
) -> bool:
    runtime = status.runtime

    return (
        runtime is not None
        and runtime.ready
        and runtime.ownership_acquired
        and runtime.hardware_initialized
    )


def _evaluate_runtime(
    status: PlatformStatusInterface,
    issues: list[HealthIssue],
) -> None:
    runtime = status.runtime

    if runtime is None:
        _add_issue(
            issues,
            component="runtime",
            severity="critical",
            message=(status.runtime_error or "Robot Runtime is unavailable."),
        )

        return

    if not runtime.ready:
        _add_issue(
            issues,
            component="runtime",
            severity="critical",
            message="Robot Runtime is not ready.",
        )

    if not runtime.ownership_acquired:
        _add_issue(
            issues,
            component="runtime",
            severity="critical",
            message=("Robot Runtime has not acquired physical hardware ownership."),
        )

    if not runtime.hardware_initialized:
        _add_issue(
            issues,
            component="runtime",
            severity="critical",
            message=("Robot Runtime hardware is not initialized."),
        )


def _evaluate_hardware(
    status: PlatformStatusInterface,
    issues: list[HealthIssue],
) -> None:
    hardware = status.hardware

    if not hardware.i2c.available:
        _add_issue(
            issues,
            component="i2c",
            severity="critical",
            message=(
                hardware.i2c.error or "Robot HAT I²C communication is unavailable."
            ),
        )

    runtime_healthy = _runtime_healthy(status)

    if runtime_healthy:
        battery = hardware.battery

        if not battery.available:
            _add_issue(
                issues,
                component="battery",
                severity="error",
                message=(battery.error or "Battery monitoring is unavailable."),
            )

        elif battery.state == "critical":
            if battery.voltage is None:
                message = "Battery voltage is critical."

            else:
                message = f"Battery voltage is critical: {battery.voltage:.2f} V."

            _add_issue(
                issues,
                component="battery",
                severity="critical",
                message=message,
            )

        elif battery.state == "low":
            if battery.voltage is None:
                message = "Battery voltage is low."

            else:
                message = f"Battery voltage is low: {battery.voltage:.2f} V."

            _add_issue(
                issues,
                component="battery",
                severity="warning",
                message=message,
            )

        elif battery.state != "ok":
            _add_issue(
                issues,
                component="battery",
                severity="warning",
                message=(f"Battery state is {battery.state}."),
            )

        sensors = hardware.sensors

        if not sensors.grayscale_available:
            _add_issue(
                issues,
                component="grayscale",
                severity="warning",
                message=(sensors.error or "Grayscale sensor is unavailable."),
            )

        elif sensors.grayscale_plausible is False:
            _add_issue(
                issues,
                component="grayscale",
                severity="warning",
                message=("Grayscale sensor readings appear abnormal."),
            )

        if not sensors.ultrasonic_configured:
            _add_issue(
                issues,
                component="ultrasonic",
                severity="warning",
                message=("Ultrasonic sensor is not configured."),
            )

        elif not sensors.ultrasonic_available:
            _add_issue(
                issues,
                component="ultrasonic",
                severity="warning",
                message=(
                    sensors.ultrasonic_error or "Ultrasonic sensor is not responding."
                ),
            )

    if not hardware.audio.available:
        _add_issue(
            issues,
            component="audio",
            severity="warning",
            message=(hardware.audio.error or "Audio device is unavailable."),
        )

    vision = hardware.vision

    if not vision.service_available:
        _add_issue(
            issues,
            component="vision",
            severity="error",
            message=(vision.error or "Vision service is unavailable."),
        )

    elif not vision.running:
        _add_issue(
            issues,
            component="vision",
            severity="error",
            message="Vision pipeline is not running.",
        )

    elif not vision.camera_running:
        _add_issue(
            issues,
            component="vision",
            severity="error",
            message="Camera is not running.",
        )

    elif not vision.camera_has_frame:
        _add_issue(
            issues,
            component="vision",
            severity="warning",
            message=("Camera is not producing frames."),
        )


def _evaluate_system(
    status: PlatformStatusInterface,
    issues: list[HealthIssue],
) -> None:
    system = status.system_health

    temperature = system.temperature

    if temperature.state == "critical":
        _add_issue(
            issues,
            component="temperature",
            severity="critical",
            message=("CPU temperature is critical."),
        )

    elif temperature.state == "high":
        _add_issue(
            issues,
            component="temperature",
            severity="warning",
            message="CPU temperature is high.",
        )

    elif temperature.error is not None:
        _add_issue(
            issues,
            component="temperature",
            severity="warning",
            message=temperature.error,
        )

    throttling = system.throttling

    if throttling.undervoltage_now:
        _add_issue(
            issues,
            component="power",
            severity="critical",
            message=("System undervoltage is currently detected."),
        )

    elif throttling.undervoltage_occurred:
        _add_issue(
            issues,
            component="power",
            severity="warning",
            message=("System undervoltage has occurred since boot."),
        )

    if throttling.throttled_now:
        _add_issue(
            issues,
            component="power",
            severity="error",
            message=("CPU throttling is currently active."),
        )

    elif throttling.throttled_occurred:
        _add_issue(
            issues,
            component="power",
            severity="warning",
            message=("CPU throttling has occurred since boot."),
        )

    memory = system.memory

    if memory.state == "critical":
        _add_issue(
            issues,
            component="memory",
            severity="critical",
            message="Memory usage is critical.",
        )

    elif memory.state == "high":
        _add_issue(
            issues,
            component="memory",
            severity="warning",
            message="Memory usage is high.",
        )

    elif memory.error is not None:
        _add_issue(
            issues,
            component="memory",
            severity="warning",
            message=memory.error,
        )

    disk = system.disk

    if disk.state == "critical":
        _add_issue(
            issues,
            component="disk",
            severity="critical",
            message="Disk usage is critical.",
        )

    elif disk.state == "high":
        _add_issue(
            issues,
            component="disk",
            severity="warning",
            message="Disk usage is high.",
        )

    elif disk.error is not None:
        _add_issue(
            issues,
            component="disk",
            severity="warning",
            message=disk.error,
        )


def _evaluate_services(
    status: PlatformStatusInterface,
    config: PlatformConfig,
    issues: list[HealthIssue],
) -> None:
    for unit, state in status.services.items():
        definition = config.services.get(unit)

        if definition is None:
            continue

        if state == "failed":
            severity: IssueSeverity = (
                "error"
                if definition.startup != ServiceStartup.CONDITIONAL
                else "warning"
            )

            _add_issue(
                issues,
                component="services",
                severity=severity,
                message=(f"{definition.display_name} service failed."),
            )

            continue

        if definition.startup == ServiceStartup.CONTINUOUS:
            if state == "active":
                continue

            if state == "activating":
                _add_issue(
                    issues,
                    component="services",
                    severity="warning",
                    message=(f"{definition.display_name} service is still starting."),
                )

                continue

            _add_issue(
                issues,
                component="services",
                severity="error",
                message=(f"{definition.display_name} service is {state}."),
            )

            continue

        if definition.startup == ServiceStartup.ONESHOT:
            if state in {
                "active",
                "inactive",
                "activating",
            }:
                continue

            _add_issue(
                issues,
                component="services",
                severity="warning",
                message=(f"{definition.display_name} service is {state}."),
            )

            continue

        # Conditional services are allowed to be inactive
        # when their condition does not currently apply.


def _evaluate_workspace(
    status: PlatformStatusInterface,
    issues: list[HealthIssue],
) -> None:
    if status.guest.ok:
        return

    _add_issue(
        issues,
        component="guest",
        severity="warning",
        message="Guest workspace is incomplete.",
    )


def _evaluate_jupyterhub(
    status: PlatformStatusInterface,
    issues: list[HealthIssue],
) -> None:
    if status.jupyterhub_proxy_available:
        return

    _add_issue(
        issues,
        component="jupyterhub",
        severity="error",
        message=("JupyterHub proxy executable is unavailable."),
    )


def evaluate_platform_health(
    status: PlatformStatusInterface,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> PlatformHealth:
    config_value = _validate_config(config)

    issues: list[HealthIssue] = []

    _evaluate_runtime(
        status,
        issues,
    )

    _evaluate_hardware(
        status,
        issues,
    )

    _evaluate_system(
        status,
        issues,
    )

    _evaluate_services(
        status,
        config_value,
        issues,
    )

    _evaluate_workspace(
        status,
        issues,
    )

    _evaluate_jupyterhub(
        status,
        issues,
    )

    return PlatformHealth(
        state=_health_state(issues),
        issues=tuple(issues),
    )


__all__ = [
    "HEALTH_STATE_ORDER",
    "HealthIssue",
    "HealthIssueData",
    "HealthState",
    "IssueSeverity",
    "PlatformHealth",
    "PlatformHealthData",
    "PlatformStatusInterface",
    "evaluate_platform_health",
]
