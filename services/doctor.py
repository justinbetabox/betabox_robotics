from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Literal, cast

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.runtime.client import (
    RobotRuntimeClient,
)
from betabox_robotics.runtime.errors import (
    RobotRuntimeError,
    RobotRuntimeUnavailableError,
)
from betabox_robotics.services.guest import (
    GuestWorkspaceStatus,
)
from betabox_robotics.services.hardware_checks.models import RobotHardwareStatus
from betabox_robotics.services.http_health import (
    check_http_available,
    check_json_health,
)
from betabox_robotics.services.managed import managed_services
from betabox_robotics.services.status import StatusReport, collect_status
from betabox_robotics.services.system_checks.models import (
    SystemHealthStatus,
)
from betabox_robotics.services.verify_checks import CheckResult, collect_checks

Severity = Literal["info", "warning", "error", "critical"]

ROBOT_HAT_I2C_ADDRESS = "0x14"

SEVERITY_ORDER: dict[Severity, int] = {
    "info": 0,
    "warning": 1,
    "error": 2,
    "critical": 3,
}

SEVERITIES: frozenset[str] = frozenset(
    {
        "info",
        "warning",
        "error",
        "critical",
    }
)


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


def _validate_flag(
    value: object,
    *,
    name: str,
) -> bool:
    if not isinstance(
        value,
        bool,
    ):
        raise TypeError(f"{name} must be a boolean")

    return value


def _validate_non_negative_int(
    value: object,
    *,
    name: str,
) -> int:
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError(f"{name} must be an integer")

    if value < 0:
        raise ValueError(f"{name} cannot be negative")

    return value


def _validate_string_list(
    value: object,
    *,
    name: str,
) -> tuple[str, ...]:
    if not isinstance(
        value,
        list | tuple,
    ):
        raise TypeError(f"{name} must be a list or tuple")

    values = cast(
        list[object] | tuple[object, ...],
        value,
    )

    return tuple(
        _validate_string(
            item,
            name=f"{name} item",
        )
        for item in values
    )


@dataclass(frozen=True, slots=True)
class Diagnosis:
    title: str
    ok: bool
    severity: Severity
    summary: str
    causes: tuple[str, ...]
    affected: tuple[str, ...]
    actions: tuple[str, ...]

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "title",
            _validate_string(
                self.title,
                name="title",
            ),
        )
        object.__setattr__(
            self,
            "ok",
            _validate_flag(
                self.ok,
                name="ok",
            ),
        )

        severity = self.severity.strip().lower()

        if severity not in SEVERITIES:
            raise ValueError("severity must be one of: critical, error, info, warning")

        object.__setattr__(
            self,
            "severity",
            cast(
                Severity,
                severity,
            ),
        )
        object.__setattr__(
            self,
            "summary",
            _validate_string(
                self.summary,
                name="summary",
            ),
        )
        object.__setattr__(
            self,
            "causes",
            _validate_string_list(
                self.causes,
                name="causes",
            ),
        )
        object.__setattr__(
            self,
            "affected",
            _validate_string_list(
                self.affected,
                name="affected",
            ),
        )
        object.__setattr__(
            self,
            "actions",
            _validate_string_list(
                self.actions,
                name="actions",
            ),
        )

        if self.ok and self.severity != "info":
            raise ValueError("healthy diagnoses must use info severity")


@dataclass(frozen=True, slots=True)
class DoctorReport:
    diagnoses: tuple[Diagnosis, ...]
    critical: int
    error: int
    warning: int
    healthy: int

    def __post_init__(
        self,
    ) -> None:
        for name in (
            "critical",
            "error",
            "warning",
            "healthy",
        ):
            value = cast(
                object,
                getattr(
                    self,
                    name,
                ),
            )

            object.__setattr__(
                self,
                name,
                _validate_non_negative_int(
                    value,
                    name=name,
                ),
            )

        counts = diagnosis_counts(self.diagnoses)

        expected = {
            "critical": self.critical,
            "error": self.error,
            "warning": self.warning,
            "healthy": self.healthy,
        }

        if counts != expected:
            raise ValueError("diagnosis counts do not match diagnoses")

    @property
    def total(self) -> int:
        return len(self.diagnoses)

    @property
    def issues(self) -> int:
        return self.critical + self.error + self.warning

    @property
    def ok(self) -> bool:
        return self.issues == 0

    @property
    def overall(self) -> str:
        if self.critical > 0:
            return "critical"

        if self.error > 0:
            return "error"

        if self.warning > 0:
            return "warning"

        return "healthy"

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": {
                "overall": self.overall,
                "ok": self.ok,
                "total": self.total,
                "issues": self.issues,
                "critical": self.critical,
                "error": self.error,
                "warning": self.warning,
                "healthy": self.healthy,
            },
            "diagnoses": [asdict(diagnosis) for diagnosis in self.diagnoses],
        }


def dedicated_service_units(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> set[str]:
    config_value = _validate_config(config)

    return {
        config_value.services.video.unit,
        config_value.services.jupyterhub.unit,
        config_value.services.boot_announce.unit,
        config_value.services.launchpad.unit,
    }


def healthy(
    title: str,
    summary: str,
) -> Diagnosis:
    return Diagnosis(
        title=title,
        ok=True,
        severity="info",
        summary=summary,
        causes=(),
        affected=(),
        actions=(),
    )


def result_map(
    results: list[CheckResult] | tuple[CheckResult, ...],
) -> dict[str, CheckResult]:
    return {result.name: result for result in results}


def diagnose_boot_announce(
    status: StatusReport,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> Diagnosis:
    unit = config.services.boot_announce.unit

    state = status.services.get(
        unit,
        "unknown",
    )

    if state in ("active", "inactive"):
        return healthy(
            "Boot Announce",
            (
                "Boot announcement service completed successfully."
                if state == "inactive"
                else "Boot announcement service is running."
            ),
        )

    if state == "failed":
        return Diagnosis(
            title="Boot Announce",
            ok=False,
            severity="warning",
            summary="The boot announcement service failed.",
            causes=(
                "The audio device was unavailable during boot.",
                "A speech backend failed.",
                "The amplifier GPIO was unavailable.",
                "A dependency was not ready when the service started.",
            ),
            affected=(
                "Startup voice announcements",
                "Teacher-facing boot status feedback",
            ),
            actions=(
                "Run: betabox logs boot-announce --journal-only",
                "Run: aplay -l",
                "Run: betabox verify",
                f"Restart: sudo systemctl restart {unit}",
            ),
        )

    return Diagnosis(
        title="Boot Announce",
        ok=False,
        severity="warning",
        summary=f"Boot announcement service state is {state}.",
        causes=(
            "The service is still starting.",
            "The service state could not be determined.",
        ),
        affected=("Startup voice announcements",),
        actions=(
            "Wait briefly and run betabox doctor again.",
            "Run: betabox services",
            "Review the boot announcement logs.",
        ),
    )


def diagnose_media(results: dict[str, CheckResult]) -> Diagnosis:
    required = (
        "media:pictures",
        "media:videos",
        "media:sounds",
    )

    missing = [
        name for name in required if not (results.get(name) and results[name].ok)
    ]

    if not missing:
        return healthy(
            "Media",
            "Media folders are available.",
        )

    return Diagnosis(
        title="Media",
        ok=False,
        severity="warning",
        summary="One or more media folders are missing.",
        causes=(
            "The installer did not create all media directories.",
            "A media directory was removed.",
        ),
        affected=(
            "Snapshots",
            "Recordings",
            "Audio files",
        ),
        actions=(
            "Run the deployment installer again.",
            "Create ~/media/pictures, ~/media/videos, and ~/media/sounds.",
            "Run: betabox status",
        ),
    )


def diagnose_guest_workspace(
    guest: GuestWorkspaceStatus,
) -> Diagnosis:
    if guest.ok:
        return healthy(
            "Guest Workspace",
            "Guest workspace is ready for classroom use.",
        )

    affected: list[str] = []

    if not guest.account_exists:
        affected.append("Guest account")

    if not guest.home_exists:
        affected.append("Guest home")

    if not guest.curriculum_exists:
        affected.append("Curriculum")

    if not guest.media_exists:
        affected.append("Media")

    if not guest.preferences_exist:
        affected.append("Preferences")

    causes: list[str] = []

    if not guest.account_exists:
        causes.append("The Guest account is missing.")

    if not guest.home_exists:
        causes.append("The Guest home directory is missing.")

    if guest.home_exists and not guest.curriculum_exists:
        causes.append("The Guest workspace was not fully provisioned.")

    if guest.home_exists and (not guest.media_exists or not guest.preferences_exist):
        causes.append("Workspace files may have been removed or corrupted.")

    return Diagnosis(
        title="Guest Workspace",
        ok=False,
        severity="error",
        summary="Guest workspace is incomplete.",
        causes=tuple(causes),
        affected=tuple(affected),
        actions=(
            "Run: betabox guest provision",
            "Restart: sudo systemctl restart betabox-guest-reset.service",
            "Run: betabox doctor",
        ),
    )


def diagnose_services(
    status: StatusReport,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> Diagnosis:
    services = managed_services(config)
    dedicated = dedicated_service_units(config)
    failed = [
        service.title
        for service in services.values()
        if (
            service.unit not in dedicated
            and status.services.get(service.unit) == "failed"
        )
    ]

    not_ready = [
        (f"{service.title} ({status.services.get(service.unit, 'unknown')})")
        for service in services.values()
        if (
            service.unit not in dedicated
            and status.services.get(
                service.unit,
                "unknown",
            )
            not in (
                "active",
                "inactive",
                "not-installed",
            )
        )
    ]

    if failed:
        return Diagnosis(
            title="Managed Services",
            ok=False,
            severity="error",
            summary="One or more managed services have failed.",
            causes=(
                "A service crashed during startup.",
                "A dependency or hardware resource is unavailable.",
                "A service unit or command may be misconfigured.",
            ),
            affected=tuple(failed),
            actions=(
                "Run: betabox services",
                "Run: betabox logs <service> --journal-only",
                "Restart the failed service.",
            ),
        )

    if not_ready:
        return Diagnosis(
            title="Managed Services",
            ok=False,
            severity="warning",
            summary="Some managed services are not ready.",
            causes=(
                "A service is still activating.",
                "A one-shot service exited unexpectedly.",
                "A service state could not be determined.",
            ),
            affected=tuple(not_ready),
            actions=(
                "Run: betabox services",
                "Wait briefly and run betabox doctor again.",
                "Review the relevant service logs.",
            ),
        )

    return healthy(
        "Managed Services",
        "No failed managed services were detected.",
    )


def diagnose_jupyterhub(
    results: dict[str, CheckResult],
    status: StatusReport,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> Diagnosis:
    proxy = results.get("jupyterhub:proxy")

    service_state = status.services.get(
        config.services.jupyterhub.unit,
        "unknown",
    )

    proxy_ok = bool(proxy and proxy.ok)

    service_ok = service_state == "active"

    health_ok = False
    health_message = "service is not active"

    if service_ok:
        health_ok, health_message = check_http_available(
            config.network.jupyterhub_health_url,
        )

    if proxy_ok and service_ok and health_ok:
        return healthy(
            "JupyterHub",
            ("JupyterHub service, proxy, and HTTP endpoint are available."),
        )

    causes: list[str] = []

    affected = [
        "Student notebook access",
        "Robot Car kernel sessions",
    ]

    actions: list[str] = []

    if not proxy_ok:
        causes.append("configurable-http-proxy is missing or unavailable.")

        actions.extend(
            [
                "Install Node.js and npm.",
                "Install configurable-http-proxy.",
            ]
        )

    if not service_ok:
        causes.append(f"{config.services.jupyterhub.unit} is {service_state}.")

        actions.extend(
            [
                (f"Restart: sudo systemctl restart {config.services.jupyterhub.unit}"),
                ("Check: betabox logs jupyterhub --journal-only"),
            ]
        )

    elif not health_ok:
        causes.append(
            f"JupyterHub service is active, but its health endpoint failed: {health_message}."
        )

        actions.extend(
            [
                (f"Check: curl --fail {config.network.jupyterhub_health_url}"),
                ("Check: betabox logs jupyterhub --journal-only"),
            ]
        )

    return Diagnosis(
        title="JupyterHub",
        ok=False,
        severity="error",
        summary=("JupyterHub is not fully available."),
        causes=tuple(causes),
        affected=tuple(affected),
        actions=tuple(actions),
    )


def diagnose_robot_hardware(
    hardware: RobotHardwareStatus,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> Diagnosis:
    if not hardware.i2c.available:
        return Diagnosis(
            title="Robot Hardware",
            ok=False,
            severity="critical",
            summary="The robot I²C bus is unavailable.",
            causes=(
                "I²C is disabled.",
                "The Robot HAT is disconnected.",
                "The I²C device node is missing.",
            ),
            affected=(
                "Robot HAT",
                "Battery monitoring",
                "Grayscale sensor",
                "Motor and servo control",
            ),
            actions=(
                "Verify dtparam=i2c_arm=on.",
                "Reboot the robot.",
                "Check that the Robot HAT is seated correctly.",
                f"Run: i2cdetect -y {config.verification.i2c_bus}",
            ),
        )

    if ROBOT_HAT_I2C_ADDRESS not in hardware.i2c.devices:
        return Diagnosis(
            title="Robot Hardware",
            ok=False,
            severity="critical",
            summary="The Robot HAT is not responding on the I²C bus.",
            causes=(
                "The Robot HAT power switch may be off.",
                "The Robot HAT may not be receiving power.",
                "The Robot HAT connection may be loose.",
                "I²C communication with the Robot HAT may have failed.",
            ),
            affected=(
                "Drive",
                "Steering",
                "Battery",
                "Sensors",
            ),
            actions=(
                "Check that the Robot HAT power switch is on.",
                "Check Robot HAT power and connections.",
                "Reseat the Robot HAT if necessary.",
                f"Run: i2cdetect -y {config.verification.i2c_bus}",
            ),
        )

    if not hardware.passive_hardware_available:
        return Diagnosis(
            title="Robot Hardware",
            ok=False,
            severity="critical",
            summary=(
                hardware.passive_hardware_error or "Robot hardware is unavailable."
            ),
            causes=(
                "Robot HAT communication failed.",
                "A required hardware component could not be constructed.",
            ),
            affected=(
                "Drive",
                "Steering",
                "Battery",
                "Sensors",
            ),
            actions=(
                "Check Robot HAT power.",
                "Reseat the Robot HAT.",
                "Run: betabox verify",
            ),
        )

    return healthy(
        "Robot Hardware",
        "Robot hardware and I²C communication are available.",
    )


def diagnose_battery(hardware: RobotHardwareStatus) -> Diagnosis:
    battery = hardware.battery

    if not battery.available or battery.voltage is None:
        return Diagnosis(
            title="Battery",
            ok=False,
            severity="error",
            summary=battery.error or "Battery voltage is unavailable.",
            causes=(
                "Battery is disconnected.",
                "Robot HAT power is unavailable.",
                "Battery monitoring hardware is not responding.",
            ),
            affected=(
                "Drive motors",
                "Steering servo",
                "Sensors",
            ),
            actions=(
                "Check the battery connector.",
                "Check Robot HAT power.",
                "Run: betabox verify",
            ),
        )

    if battery.state == "critical":
        return Diagnosis(
            title="Battery",
            ok=False,
            severity="critical",
            summary=f"Battery voltage is critical: {battery.voltage:.2f} V.",
            causes=(
                "Battery is discharged.",
                "Battery voltage dropped under load.",
                "Battery or connector may be damaged.",
            ),
            affected=(
                "Drive motors",
                "Steering servo",
                "Robot stability",
            ),
            actions=(
                "Stop driving the robot.",
                "Recharge or replace the battery.",
                "Inspect and reseat the battery connector.",
                "Run: betabox verify",
            ),
        )

    if battery.state == "low":
        return Diagnosis(
            title="Battery",
            ok=False,
            severity="warning",
            summary=f"Battery voltage is low: {battery.voltage:.2f} V.",
            causes=(
                "Battery is partially discharged.",
                "Recent motor use reduced battery voltage.",
            ),
            affected=(
                "Drive runtime",
                "Servo reliability",
            ),
            actions=(
                "Recharge the battery before extended use.",
                "Avoid high-load driving until recharged.",
            ),
        )

    return healthy(
        "Battery",
        f"Battery voltage is healthy: {battery.voltage:.2f} V.",
    )


def diagnose_grayscale(
    hardware: RobotHardwareStatus,
) -> Diagnosis:
    sensors = hardware.sensors

    if not sensors.grayscale_available:
        return Diagnosis(
            title="Grayscale",
            ok=False,
            severity="warning",
            summary=sensors.error or "Grayscale sensor is unavailable.",
            causes=(
                "The grayscale sensor cable is disconnected.",
                "The Robot HAT ADC is unavailable.",
                "The sensor hardware is not responding.",
            ),
            affected=(
                "Line following",
                "Line avoidance",
                "Surface reflectance readings",
            ),
            actions=(
                "Check the grayscale sensor cable.",
                "Check the Robot HAT connection.",
                "Run the grayscale validation test.",
            ),
        )

    values = sensors.grayscale_values or ()

    if sensors.grayscale_plausible is False:
        channel_names = (
            "left",
            "middle",
            "right",
        )

        suspicious_channels = tuple(
            channel_names[channel]
            for channel in sensors.grayscale_suspicious_channels
            if 0 <= channel < len(channel_names)
        )

        if len(suspicious_channels) == len(channel_names):
            summary = (
                "All grayscale sensor channels are reporting implausibly high values."
            )
            causes = (
                "The grayscale sensor module may be disconnected.",
                "The grayscale sensor cable may be loose or damaged.",
                "The grayscale sensor module may be faulty.",
            )
        elif suspicious_channels:
            names = ", ".join(suspicious_channels)
            summary = f"Grayscale sensor readings appear abnormal on: {names}."
            causes = (
                "One or more grayscale sensors may be disconnected or faulty.",
                "The grayscale sensor cable may be loose or damaged.",
                "The affected sensor may not be responding correctly.",
            )
        else:
            summary = "Grayscale sensor readings appear abnormal."
            causes = (
                "The grayscale sensor module may be disconnected or faulty.",
                "The grayscale sensor cable may be loose or damaged.",
            )

        if values:
            summary += " Values: " + ", ".join(str(value) for value in values)

        return Diagnosis(
            title="Grayscale",
            ok=False,
            severity="warning",
            summary=summary,
            causes=causes,
            affected=(
                "Line following",
                "Line avoidance",
                "Surface reflectance readings",
            ),
            actions=(
                "Check the grayscale sensor cable.",
                "Check that all three grayscale sensors are responding.",
                "Run the grayscale validation test.",
            ),
        )

    summary = "Grayscale sensor is available."

    if values:
        summary += " Values: " + ", ".join(str(value) for value in values)

    return healthy(
        "Grayscale",
        summary,
    )


def diagnose_ultrasonic() -> Diagnosis:
    try:
        client = RobotRuntimeClient()

        distance = client.ultrasonic_distance(
            samples=1,
        )

    except RobotRuntimeUnavailableError as exc:
        return Diagnosis(
            title="Ultrasonic",
            ok=False,
            severity="warning",
            summary=(
                "Ultrasonic sensor could not be tested "
                "because the robot runtime is unavailable."
            ),
            causes=(str(exc),),
            affected=("Ultrasonic diagnostic test",),
            actions=(
                "Check: systemctl status betabox-robot.service",
                "Restart: sudo systemctl restart betabox-robot.service",
                "Run the diagnostic again.",
            ),
        )

    except RobotRuntimeError as exc:
        return Diagnosis(
            title="Ultrasonic",
            ok=False,
            severity="warning",
            summary="Ultrasonic sensor is not responding.",
            causes=(
                str(exc),
                "The ultrasonic sensor may be disconnected.",
                "The ultrasonic sensor cable may be loose or damaged.",
                "The trigger or echo connection may not be working.",
            ),
            affected=(
                "Distance sensing",
                "Obstacle detection",
                "Obstacle avoidance",
            ),
            actions=(
                "Check the ultrasonic sensor connection.",
                "Check the trigger and echo connections.",
                "Run the ultrasonic validation test.",
            ),
        )

    if distance < 0:
        return Diagnosis(
            title="Ultrasonic",
            ok=False,
            severity="warning",
            summary=(
                f"Ultrasonic sensor returned an invalid distance: {distance:.1f} cm."
            ),
            causes=(
                "The ultrasonic sensor did not produce a valid distance measurement.",
            ),
            affected=(
                "Distance sensing",
                "Obstacle detection",
                "Obstacle avoidance",
            ),
            actions=(
                "Check the ultrasonic sensor connection.",
                "Run the ultrasonic validation test.",
            ),
        )

    return healthy(
        "Ultrasonic",
        (f"Ultrasonic sensor is responding. Distance: {distance:.1f} cm."),
    )


def diagnose_audio_hardware(
    hardware: RobotHardwareStatus,
) -> Diagnosis:
    audio = hardware.audio

    if audio.available:
        return healthy(
            "Audio Hardware",
            f"Audio device is available: {audio.device}.",
        )

    return Diagnosis(
        title="Audio Hardware",
        ok=False,
        severity="warning",
        summary=audio.error or "Audio device is unavailable.",
        causes=(
            "The HifiBerry overlay is missing.",
            "The audio device failed to initialize.",
            "The audio hardware is disconnected.",
        ),
        affected=(
            "Speech output",
            "Sound playback",
            "Tones and melodies",
        ),
        actions=(
            "Run: aplay -l",
            "Verify dtoverlay=hifiberry-dac is configured.",
            "Reboot after changing audio overlays.",
        ),
    )


def diagnose_vision_hardware(
    hardware: RobotHardwareStatus,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> Diagnosis:
    vision = hardware.vision

    if not vision.service_available:
        return Diagnosis(
            title="Vision",
            ok=False,
            severity="error",
            summary=vision.error or "Vision service is unavailable.",
            causes=(
                f"{config.services.video.unit} is stopped or failed.",
                "The Vision API is not responding.",
                "The service failed during camera startup.",
            ),
            affected=(
                "WebRTC streaming",
                "Snapshots",
                "Recording",
                "Detection",
            ),
            actions=(
                "Run: betabox services",
                "Run: betabox logs video --journal-only",
                f"Restart: sudo systemctl restart {config.services.video.unit}",
            ),
        )

    if not vision.running:
        return Diagnosis(
            title="Vision",
            ok=False,
            severity="error",
            summary="Vision service is responding but the runtime is stopped.",
            causes=(
                "VisionService failed to start.",
                "Camera initialization failed.",
            ),
            affected=(
                "Streaming",
                "Snapshots",
                "Recording",
                "Detection",
            ),
            actions=(
                f"Restart: sudo systemctl restart {config.services.video.unit}",
                "Run: betabox logs video --journal-only",
                "Check the camera ribbon cable.",
            ),
        )

    if not vision.camera_running:
        return Diagnosis(
            title="Vision",
            ok=False,
            severity="error",
            summary="Vision runtime is active, but the camera is stopped.",
            causes=(
                "Camera initialization failed.",
                "Camera hardware is disconnected.",
                "Another process may have opened the camera.",
            ),
            affected=(
                "Streaming",
                "Snapshots",
                "Recording",
                "Detection",
            ),
            actions=(
                "Check the camera ribbon cable.",
                "Check for another camera process.",
                f"Restart: sudo systemctl restart {config.services.video.unit}",
            ),
        )

    if not vision.camera_has_frame:
        return Diagnosis(
            title="Vision",
            ok=False,
            severity="warning",
            summary="The camera is running, but no recent frame is available.",
            causes=(
                "The capture loop may be stalled.",
                "The camera stopped returning frames.",
            ),
            affected=(
                "Live video",
                "Snapshots",
                "Recording",
                "Detection",
            ),
            actions=(
                f"Check: {config.network.vision_url}/stats",
                f"Restart: sudo systemctl restart {config.services.video.unit}",
                "Review the video service logs.",
            ),
        )

    return healthy(
        "Vision",
        "Vision service and camera pipeline are healthy.",
    )


def diagnose_launchpad(
    status: StatusReport,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> Diagnosis:
    unit = config.services.launchpad.unit

    service_state = status.services.get(
        unit,
        "unknown",
    )

    if service_state != "active":
        return Diagnosis(
            title="Launchpad",
            ok=False,
            severity="error",
            summary=(f"Launchpad is not available because {unit} is {service_state}."),
            causes=(
                "The Launchpad service failed during startup.",
                "The service unit or startup command is misconfigured.",
                "Another process may already be using the Launchpad port.",
            ),
            affected=(
                "Launchpad dashboard",
                "Manual Drive",
                "Live camera page",
                "Browser-based platform tools",
            ),
            actions=(
                "Run: betabox services",
                "Run: betabox logs launchpad --journal-only",
                f"Restart: sudo systemctl restart {unit}",
            ),
        )

    health_ok, health_message = check_json_health(
        config.network.launchpad_health_url,
        expected_service="launchpad",
    )

    if health_ok:
        return healthy(
            "Launchpad",
            "Launchpad service and HTTP API are healthy.",
        )

    return Diagnosis(
        title="Launchpad",
        ok=False,
        severity="error",
        summary=(
            "Launchpad service is active, but its "
            f"health endpoint failed: {health_message}."
        ),
        causes=(
            "The aiohttp application did not start correctly.",
            "The Launchpad event loop may be stalled.",
            "The configured host or port may not match the service.",
            "The health route may be missing or returning invalid data.",
        ),
        affected=(
            "Launchpad dashboard",
            "Manual Drive",
            "Live camera page",
            "Browser-based platform tools",
        ),
        actions=(
            (f"Check: curl --fail {config.network.launchpad_health_url}"),
            "Run: betabox logs launchpad --journal-only",
            f"Restart: sudo systemctl restart {unit}",
        ),
    )


def collect_diagnoses(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> tuple[Diagnosis, ...]:
    status = collect_status(config)

    checks = collect_checks(
        include_robot=False,
        config=config,
    )

    results = result_map(checks)

    hardware = status.hardware

    system = status.system_health

    robot_hardware = diagnose_robot_hardware(hardware, config)
    vision = diagnose_vision_hardware(hardware, config)
    runtime = diagnose_robot_runtime(status)

    diagnoses: list[Diagnosis] = [
        diagnose_temperature(system),
        diagnose_power(system),
        runtime,
        robot_hardware,
        diagnose_guest_workspace(status.guest),
        diagnose_audio_hardware(hardware),
        vision,
        diagnose_jupyterhub(results, status, config),
        diagnose_launchpad(
            status,
            config,
        ),
        diagnose_boot_announce(status, config),
        diagnose_media(results),
        diagnose_services(status, config),
    ]

    if robot_hardware.ok:
        diagnoses.append(diagnose_battery(hardware))
        diagnoses.append(diagnose_grayscale(hardware))

        if runtime.ok:
            diagnoses.append(diagnose_ultrasonic())

    return tuple(diagnoses)


def diagnose_temperature(status: SystemHealthStatus) -> Diagnosis:
    temperature = status.temperature

    if temperature.celsius is None:
        return Diagnosis(
            title="CPU Temperature",
            ok=False,
            severity="warning",
            summary=temperature.error or "CPU temperature is unavailable.",
            causes=("Thermal sensor data could not be read.",),
            affected=("Thermal monitoring",),
            actions=("Check /sys/class/thermal/thermal_zone0/temp.",),
        )

    if temperature.state == "critical":
        return Diagnosis(
            title="CPU Temperature",
            ok=False,
            severity="critical",
            summary=f"CPU temperature is critical: {temperature.celsius:.1f} °C.",
            causes=(
                "Insufficient cooling.",
                "Heavy sustained CPU load.",
                "Blocked airflow.",
            ),
            affected=(
                "Camera performance",
                "Vision inference",
                "System stability",
            ),
            actions=(
                "Stop high-load workloads.",
                "Check the fan and heatsink.",
                "Improve airflow.",
                "Reboot after the system cools.",
            ),
        )

    if temperature.state == "high":
        return Diagnosis(
            title="CPU Temperature",
            ok=False,
            severity="warning",
            summary=f"CPU temperature is high: {temperature.celsius:.1f} °C.",
            causes=(
                "High CPU load.",
                "Cooling may be insufficient.",
            ),
            affected=(
                "Performance",
                "Vision frame rate",
            ),
            actions=(
                "Check cooling and airflow.",
                "Review running processes.",
            ),
        )

    return healthy(
        "CPU Temperature",
        f"CPU temperature is normal: {temperature.celsius:.1f} °C.",
    )


def diagnose_power(status: SystemHealthStatus) -> Diagnosis:
    throttling = status.throttling

    if throttling.undervoltage_now:
        return Diagnosis(
            title="System Power",
            ok=False,
            severity="critical",
            summary="The Raspberry Pi is currently experiencing undervoltage.",
            causes=(
                "Power supply cannot provide enough current.",
                "Power cable has excessive resistance.",
                "Robot load is causing a voltage drop.",
            ),
            affected=(
                "System stability",
                "Camera",
                "USB devices",
                "Networking",
            ),
            actions=(
                "Use a higher-quality power supply.",
                "Inspect the power cable and connectors.",
                "Reduce load and retest.",
            ),
        )

    if throttling.throttled_now:
        return Diagnosis(
            title="System Power",
            ok=False,
            severity="error",
            summary="The Raspberry Pi is currently throttled.",
            causes=(
                "Undervoltage.",
                "Excessive temperature.",
            ),
            affected=(
                "CPU performance",
                "Vision frame rate",
            ),
            actions=(
                "Check power and temperature.",
                "Review: vcgencmd get_throttled",
            ),
        )

    if throttling.undervoltage_occurred or throttling.throttled_occurred:
        return Diagnosis(
            title="System Power",
            ok=False,
            severity="warning",
            summary="A power or throttling event has occurred since boot.",
            causes=(
                "Earlier undervoltage.",
                "Earlier thermal throttling.",
            ),
            affected=("Historical system reliability",),
            actions=(
                "Run: vcgencmd get_throttled",
                "Check power and cooling.",
            ),
        )

    return healthy(
        "System Power",
        "No undervoltage or throttling is currently detected.",
    )


def diagnose_robot_runtime(
    status: StatusReport,
) -> Diagnosis:
    runtime = status.runtime

    if runtime is None:
        return Diagnosis(
            title="Robot Runtime",
            ok=False,
            severity="error",
            summary="The Betabox Robot Runtime is unavailable.",
            causes=(status.runtime_error or "The runtime service is not responding.",),
            affected=(
                "Robot API",
                "Drive and steering",
                "Robot sensors",
                "Camera mount control",
                "Calibration previews",
            ),
            actions=(
                "Check: systemctl status betabox-robot.service",
                "Restart: sudo systemctl restart betabox-robot.service",
                "Run: betabox doctor",
            ),
        )

    if (
        not runtime.ready
        or not runtime.ownership_acquired
        or not runtime.hardware_initialized
    ):
        return Diagnosis(
            title="Robot Runtime",
            ok=False,
            severity="error",
            summary="The Betabox Robot Runtime is not fully ready.",
            causes=(
                "Runtime startup did not complete.",
                "Robot hardware ownership was not acquired.",
                "Robot hardware initialization failed.",
            ),
            affected=(
                "Robot API",
                "Drive and steering",
                "Robot sensors",
                "Camera mount control",
            ),
            actions=(
                "Check: systemctl status betabox-robot.service",
                "Run: journalctl -u betabox-robot.service -n 100",
                "Restart: sudo systemctl restart betabox-robot.service",
            ),
        )

    return healthy(
        "Robot Runtime",
        "Robot Runtime and hardware ownership are ready.",
    )


def diagnosis_counts(
    diagnoses: list[Diagnosis] | tuple[Diagnosis, ...],
) -> dict[str, int]:
    return {
        "critical": sum(
            1
            for diagnosis in diagnoses
            if (not diagnosis.ok and diagnosis.severity == "critical")
        ),
        "error": sum(
            1
            for diagnosis in diagnoses
            if (not diagnosis.ok and diagnosis.severity == "error")
        ),
        "warning": sum(
            1
            for diagnosis in diagnoses
            if (not diagnosis.ok and diagnosis.severity == "warning")
        ),
        "healthy": sum(1 for diagnosis in diagnoses if diagnosis.ok),
    }


def collect_doctor_report(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> DoctorReport:
    """
    Collect and summarize all platform diagnoses.
    """

    diagnoses = collect_diagnoses(config)

    diagnoses = tuple(
        sorted(
            diagnoses,
            key=lambda diagnosis: (
                diagnosis.ok,
                -SEVERITY_ORDER[diagnosis.severity],
                diagnosis.title,
            ),
        )
    )

    counts = diagnosis_counts(diagnoses)

    return DoctorReport(
        diagnoses=diagnoses,
        critical=counts["critical"],
        error=counts["error"],
        warning=counts["warning"],
        healthy=counts["healthy"],
    )


def print_diagnoses(diagnoses: list[Diagnosis] | tuple[Diagnosis, ...]) -> bool:
    print()
    print("Betabox Doctor")
    print("==============")
    print()

    counts = diagnosis_counts(diagnoses)

    print("Platform Summary")
    print("----------------")
    print(f"Critical: {counts['critical']}")
    print(f"Errors:   {counts['error']}")
    print(f"Warnings: {counts['warning']}")
    print(f"Healthy:  {counts['healthy']}")
    print()

    all_ok = True

    for diagnosis in diagnoses:
        status = "OK" if diagnosis.ok else diagnosis.severity.upper()

        print(f"[{status}] {diagnosis.title}")
        print(f"      {diagnosis.summary}")

        if diagnosis.causes:
            print()
            print("      Likely causes:")
            for cause in diagnosis.causes:
                print(f"      - {cause}")

        if diagnosis.affected:
            print()
            print("      Affected components:")
            for component in diagnosis.affected:
                print(f"      - {component}")

        if diagnosis.actions:
            print()
            print("      Recommended actions:")
            for index, action in enumerate(diagnosis.actions, start=1):
                print(f"      {index}. {action}")

        print()

        if not diagnosis.ok:
            all_ok = False

    if all_ok:
        print("No major platform issues detected.")
    else:
        print("One or more issues were detected.")

    print()
    return all_ok


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="betabox doctor")

    _ = parser.add_argument(
        "--json",
        action="store_true",
        help=("print the diagnostic report as JSON"),
    )

    args = parser.parse_args(argv)

    json_requested = _validate_flag(
        cast(
            object,
            args.json,
        ),
        name="json",
    )

    config = DEFAULT_PLATFORM_CONFIG

    report = collect_doctor_report(config)

    if json_requested:
        print(
            json.dumps(
                report.to_dict(),
                indent=2,
            )
        )
    else:
        _ = print_diagnoses(report.diagnoses)

    return 0 if report.ok else 1


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
