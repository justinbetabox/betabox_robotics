from __future__ import annotations

import json

import argparse
from dataclasses import asdict, dataclass
from typing import Literal

from betabox_robotics.services.managed import managed_services
from betabox_robotics.services.verify import CheckResult, collect_checks
from betabox_robotics.services.hardware_status import RobotHardwareStatus
from betabox_robotics.services.status import StatusReport, collect_status
from betabox_robotics.services.system_health import (
    SystemHealthStatus,
)
from betabox_robotics.services.http_health import (
    check_http_available,
    check_json_health,
)

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)


Severity = Literal["info", "warning", "error", "critical"]

SEVERITY_ORDER: dict[Severity, int] = {
    "info": 0,
    "warning": 1,
    "error": 2,
    "critical": 3,
}

@dataclass(frozen=True)
class Diagnosis:
    title: str
    ok: bool
    severity: Severity
    summary: str
    causes: list[str]
    affected: list[str]
    actions: list[str]

@dataclass(frozen=True)
class DoctorReport:
    """
    Complete diagnostic report for the Betabox Platform.

    This model is shared by the CLI and Launchpad diagnostics page.
    """

    diagnoses: list[Diagnosis]
    critical: int
    error: int
    warning: int
    healthy: int

    @property
    def total(self) -> int:
        return len(self.diagnoses)

    @property
    def issues(self) -> int:
        return (
            self.critical
            + self.error
            + self.warning
        )

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
            "diagnoses": [
                asdict(diagnosis)
                for diagnosis in self.diagnoses
            ],
        }

def dedicated_service_units(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> set[str]:
    return {
        config.services.video.unit,
        config.services.jupyterhub.unit,
        config.services.boot_announce.unit,
        config.services.launchpad.unit,
    }

def healthy(title: str, summary: str) -> Diagnosis:
    return Diagnosis(
        title=title,
        ok=True,
        severity="info",
        summary=summary,
        causes=[],
        affected=[],
        actions=[],
    )


def result_map(results: list[CheckResult]) -> dict[str, CheckResult]:
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
            causes=[
                "The audio device was unavailable during boot.",
                "A speech backend failed.",
                "The amplifier GPIO was unavailable.",
                "A dependency was not ready when the service started.",
            ],
            affected=[
                "Startup voice announcements",
                "Teacher-facing boot status feedback",
            ],
            actions=[
                "Run: betabox logs boot-announce --journal-only",
                "Run: aplay -l",
                "Run: betabox verify",
                f"Restart: sudo systemctl restart {unit}",
            ],
        )

    return Diagnosis(
        title="Boot Announce",
        ok=False,
        severity="warning",
        summary=f"Boot announcement service state is {state}.",
        causes=[
            "The service is still starting.",
            "The service state could not be determined.",
        ],
        affected=[
            "Startup voice announcements",
        ],
        actions=[
            "Wait briefly and run betabox doctor again.",
            "Run: betabox services",
            "Review the boot announcement logs.",
        ],
    )

def diagnose_media(results: dict[str, CheckResult]) -> Diagnosis:
    required = [
        "media:pictures",
        "media:videos",
        "media:sounds",
    ]

    missing = [
        name
        for name in required
        if not (results.get(name) and results[name].ok)
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
        causes=[
            "The installer did not create all media directories.",
            "A media directory was removed.",
        ],
        affected=[
            "Snapshots",
            "Recordings",
            "Audio files",
        ],
        actions=[
            "Run the deployment installer again.",
            "Create ~/media/pictures, ~/media/videos, and ~/media/sounds.",
            "Run: betabox status",
        ],
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
        (
            f"{service.title} "
            f"({status.services.get(service.unit, 'unknown')})"
        )
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
            causes=[
                "A service crashed during startup.",
                "A dependency or hardware resource is unavailable.",
                "A service unit or command may be misconfigured.",
            ],
            affected=failed,
            actions=[
                "Run: betabox services",
                "Run: betabox logs <service> --journal-only",
                "Restart the failed service.",
            ],
        )

    if not_ready:
        return Diagnosis(
            title="Managed Services",
            ok=False,
            severity="warning",
            summary="Some managed services are not ready.",
            causes=[
                "A service is still activating.",
                "A one-shot service exited unexpectedly.",
                "A service state could not be determined.",
            ],
            affected=not_ready,
            actions=[
                "Run: betabox services",
                "Wait briefly and run betabox doctor again.",
                "Review the relevant service logs.",
            ],
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
    proxy = results.get(
        "jupyterhub:proxy"
    )

    service_state = status.services.get(
        config.services.jupyterhub.unit,
        "unknown",
    )

    proxy_ok = bool(
        proxy and proxy.ok
    )

    service_ok = (
        service_state == "active"
    )

    health_ok = False
    health_message = (
        "service is not active"
    )

    if service_ok:
        health_ok, health_message = (
            check_http_available(
                config.network.jupyterhub_health_url,
            )
        )

    if (
        proxy_ok
        and service_ok
        and health_ok
    ):
        return healthy(
            "JupyterHub",
            (
                "JupyterHub service, proxy, "
                "and HTTP endpoint are available."
            ),
        )

    causes: list[str] = []

    affected = [
        "Student notebook access",
        "Robot Car kernel sessions",
    ]

    actions: list[str] = []

    if not proxy_ok:
        causes.append(
            "configurable-http-proxy is missing or unavailable."
        )

        actions.extend(
            [
                "Install Node.js and npm.",
                "Install configurable-http-proxy.",
            ]
        )

    if not service_ok:
        causes.append(
            f"{config.services.jupyterhub.unit} is {service_state}."
        )

        actions.extend(
            [
                (
                    "Restart: sudo systemctl restart "
                    f"{config.services.jupyterhub.unit}"
                ),
                (
                    "Check: betabox logs "
                    "jupyterhub --journal-only"
                ),
            ]
        )

    elif not health_ok:
        causes.append(
            (
                "JupyterHub service is active, "
                "but its health endpoint failed: "
                f"{health_message}."
            )
        )

        actions.extend(
            [
                (
                    "Check: curl --fail "
                    f"{config.network.jupyterhub_health_url}"
                ),
                (
                    "Check: betabox logs "
                    "jupyterhub --journal-only"
                ),
            ]
        )

    return Diagnosis(
        title="JupyterHub",
        ok=False,
        severity="error",
        summary=(
            "JupyterHub is not fully available."
        ),
        causes=causes,
        affected=affected,
        actions=actions,
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
            causes=[
                "I²C is disabled.",
                "The Robot HAT is disconnected.",
                "The I²C device node is missing.",
            ],
            affected=[
                "Robot HAT",
                "Battery monitoring",
                "Grayscale sensor",
                "Motor and servo control",
            ],
            actions=[
                "Verify dtparam=i2c_arm=on.",
                "Reboot the robot.",
                "Check that the Robot HAT is seated correctly.",
                f"Run: i2cdetect -y {config.verification.i2c_bus}",
            ],
        )

    if not hardware.passive_hardware_available:
        return Diagnosis(
            title="Robot Hardware",
            ok=False,
            severity="critical",
            summary=hardware.passive_hardware_error or "Robot hardware is unavailable.",
            causes=[
                "Robot HAT communication failed.",
                "A required hardware component could not be constructed.",
            ],
            affected=[
                "Drive",
                "Steering",
                "Battery",
                "Sensors",
            ],
            actions=[
                "Check Robot HAT power.",
                "Reseat the Robot HAT.",
                "Run: betabox verify",
            ],
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
            causes=[
                "Battery is disconnected.",
                "Robot HAT power is unavailable.",
                "Battery monitoring hardware is not responding.",
            ],
            affected=[
                "Drive motors",
                "Steering servo",
                "Sensors",
            ],
            actions=[
                "Check the battery connector.",
                "Check Robot HAT power.",
                "Run: betabox verify",
            ],
        )

    if battery.state == "critical":
        return Diagnosis(
            title="Battery",
            ok=False,
            severity="critical",
            summary=f"Battery voltage is critical: {battery.voltage:.2f} V.",
            causes=[
                "Battery is discharged.",
                "Battery voltage dropped under load.",
                "Battery or connector may be damaged.",
            ],
            affected=[
                "Drive motors",
                "Steering servo",
                "Robot stability",
            ],
            actions=[
                "Stop driving the robot.",
                "Recharge or replace the battery.",
                "Inspect and reseat the battery connector.",
                "Run: betabox verify",
            ],
        )

    if battery.state == "low":
        return Diagnosis(
            title="Battery",
            ok=False,
            severity="warning",
            summary=f"Battery voltage is low: {battery.voltage:.2f} V.",
            causes=[
                "Battery is partially discharged.",
                "Recent motor use reduced battery voltage.",
            ],
            affected=[
                "Drive runtime",
                "Servo reliability",
            ],
            actions=[
                "Recharge the battery before extended use.",
                "Avoid high-load driving until recharged.",
            ],
        )

    return healthy(
        "Battery",
        f"Battery voltage is healthy: {battery.voltage:.2f} V.",
    )


def diagnose_grayscale(
    hardware: RobotHardwareStatus,
) -> Diagnosis:
    sensors = hardware.sensors

    if sensors.grayscale_available:
        values = sensors.grayscale_values or []

        summary = "Grayscale sensor is available."

        if values:
            summary += " Values: " + ", ".join(
                str(value) for value in values
            )

        return healthy(
            "Grayscale",
            summary,
        )

    return Diagnosis(
        title="Grayscale",
        ok=False,
        severity="warning",
        summary=sensors.error or "Grayscale sensor is unavailable.",
        causes=[
            "The grayscale sensor cable is disconnected.",
            "The Robot HAT ADC is unavailable.",
            "The sensor hardware is not responding.",
        ],
        affected=[
            "Line following",
            "Line avoidance",
            "Surface reflectance readings",
        ],
        actions=[
            "Check the grayscale sensor cable.",
            "Check the Robot HAT connection.",
            "Run the grayscale validation test.",
        ],
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
        causes=[
            "The HifiBerry overlay is missing.",
            "The audio device failed to initialize.",
            "The audio hardware is disconnected.",
        ],
        affected=[
            "Speech output",
            "Sound playback",
            "Tones and melodies",
        ],
        actions=[
            "Run: aplay -l",
            "Verify dtoverlay=hifiberry-dac is configured.",
            "Reboot after changing audio overlays.",
        ],
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
            causes=[
                f"{config.services.video.unit} is stopped or failed.",
                "The Vision API is not responding.",
                "The service failed during camera startup.",
            ],
            affected=[
                "WebRTC streaming",
                "Snapshots",
                "Recording",
                "Detection",
            ],
            actions=[
                "Run: betabox services",
                "Run: betabox logs video --journal-only",
                f"Restart: sudo systemctl restart {config.services.video.unit}",
            ],
        )

    if not vision.running:
        return Diagnosis(
            title="Vision",
            ok=False,
            severity="error",
            summary="Vision service is responding but the runtime is stopped.",
            causes=[
                "VisionService failed to start.",
                "Camera initialization failed.",
            ],
            affected=[
                "Streaming",
                "Snapshots",
                "Recording",
                "Detection",
            ],
            actions=[
                f"Restart: sudo systemctl restart {config.services.video.unit}",
                "Run: betabox logs video --journal-only",
                "Check the camera ribbon cable.",
            ],
        )

    if not vision.camera_running:
        return Diagnosis(
            title="Vision",
            ok=False,
            severity="error",
            summary="Vision runtime is active, but the camera is stopped.",
            causes=[
                "Camera initialization failed.",
                "Camera hardware is disconnected.",
                "Another process may have opened the camera.",
            ],
            affected=[
                "Streaming",
                "Snapshots",
                "Recording",
                "Detection",
            ],
            actions=[
                "Check the camera ribbon cable.",
                "Check for another camera process.",
                f"Restart: sudo systemctl restart {config.services.video.unit}",
            ],
        )

    if not vision.camera_has_frame:
        return Diagnosis(
            title="Vision",
            ok=False,
            severity="warning",
            summary="The camera is running, but no recent frame is available.",
            causes=[
                "The capture loop may be stalled.",
                "The camera stopped returning frames.",
            ],
            affected=[
                "Live video",
                "Snapshots",
                "Recording",
                "Detection",
            ],
            actions=[
                f"Check: {config.network.vision_url}/stats",
                f"Restart: sudo systemctl restart {config.services.video.unit}",
                "Review the video service logs.",
            ],
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
            summary=(
                "Launchpad is not available because "
                f"{unit} is {service_state}."
            ),
            causes=[
                "The Launchpad service failed during startup.",
                "The service unit or startup command is misconfigured.",
                "Another process may already be using the Launchpad port.",
            ],
            affected=[
                "Launchpad dashboard",
                "Manual Drive",
                "Live camera page",
                "Browser-based platform tools",
            ],
            actions=[
                "Run: betabox services",
                "Run: betabox logs launchpad --journal-only",
                f"Restart: sudo systemctl restart {unit}",
            ],
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
        causes=[
            "The aiohttp application did not start correctly.",
            "The Launchpad event loop may be stalled.",
            "The configured host or port may not match the service.",
            "The health route may be missing or returning invalid data.",
        ],
        affected=[
            "Launchpad dashboard",
            "Manual Drive",
            "Live camera page",
            "Browser-based platform tools",
        ],
        actions=[
            (
                "Check: curl --fail "
                f"{config.network.launchpad_health_url}"
            ),
            "Run: betabox logs launchpad --journal-only",
            f"Restart: sudo systemctl restart {unit}",
        ],
    )

def collect_diagnoses(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> list[Diagnosis]:
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

    diagnoses = [
        diagnose_temperature(system),
        diagnose_power(system),

        robot_hardware,
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

    return diagnoses

def diagnose_temperature(status: SystemHealthStatus) -> Diagnosis:
    temperature = status.temperature

    if temperature.celsius is None:
        return Diagnosis(
            title="CPU Temperature",
            ok=False,
            severity="warning",
            summary=temperature.error or "CPU temperature is unavailable.",
            causes=["Thermal sensor data could not be read."],
            affected=["Thermal monitoring"],
            actions=["Check /sys/class/thermal/thermal_zone0/temp."],
        )

    if temperature.state == "critical":
        return Diagnosis(
            title="CPU Temperature",
            ok=False,
            severity="critical",
            summary=f"CPU temperature is critical: {temperature.celsius:.1f} °C.",
            causes=[
                "Insufficient cooling.",
                "Heavy sustained CPU load.",
                "Blocked airflow.",
            ],
            affected=[
                "Camera performance",
                "Vision inference",
                "System stability",
            ],
            actions=[
                "Stop high-load workloads.",
                "Check the fan and heatsink.",
                "Improve airflow.",
                "Reboot after the system cools.",
            ],
        )

    if temperature.state == "high":
        return Diagnosis(
            title="CPU Temperature",
            ok=False,
            severity="warning",
            summary=f"CPU temperature is high: {temperature.celsius:.1f} °C.",
            causes=[
                "High CPU load.",
                "Cooling may be insufficient.",
            ],
            affected=[
                "Performance",
                "Vision frame rate",
            ],
            actions=[
                "Check cooling and airflow.",
                "Review running processes.",
            ],
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
            causes=[
                "Power supply cannot provide enough current.",
                "Power cable has excessive resistance.",
                "Robot load is causing a voltage drop.",
            ],
            affected=[
                "System stability",
                "Camera",
                "USB devices",
                "Networking",
            ],
            actions=[
                "Use a higher-quality power supply.",
                "Inspect the power cable and connectors.",
                "Reduce load and retest.",
            ],
        )

    if throttling.throttled_now:
        return Diagnosis(
            title="System Power",
            ok=False,
            severity="error",
            summary="The Raspberry Pi is currently throttled.",
            causes=[
                "Undervoltage.",
                "Excessive temperature.",
            ],
            affected=[
                "CPU performance",
                "Vision frame rate",
            ],
            actions=[
                "Check power and temperature.",
                "Review: vcgencmd get_throttled",
            ],
        )

    if throttling.undervoltage_occurred or throttling.throttled_occurred:
        return Diagnosis(
            title="System Power",
            ok=False,
            severity="warning",
            summary="A power or throttling event has occurred since boot.",
            causes=[
                "Earlier undervoltage.",
                "Earlier thermal throttling.",
            ],
            affected=["Historical system reliability"],
            actions=[
                "Run: vcgencmd get_throttled",
                "Check power and cooling.",
            ],
        )

    return healthy(
        "System Power",
        "No undervoltage or throttling is currently detected.",
    )

def diagnosis_counts(
    diagnoses: list[Diagnosis],
) -> dict[str, int]:
    return {
        "critical": sum(
            1
            for diagnosis in diagnoses
            if not diagnosis.ok and diagnosis.severity == "critical"
        ),
        "error": sum(
            1
            for diagnosis in diagnoses
            if not diagnosis.ok and diagnosis.severity == "error"
        ),
        "warning": sum(
            1
            for diagnosis in diagnoses
            if not diagnosis.ok and diagnosis.severity == "warning"
        ),
        "healthy": sum(
            1
            for diagnosis in diagnoses
            if diagnosis.ok
        ),
    }

def collect_doctor_report(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> DoctorReport:
    """
    Collect and summarize all platform diagnoses.
    """

    diagnoses = collect_diagnoses(
        config
    )

    diagnoses = sorted(
        diagnoses,
        key=lambda diagnosis: (
            diagnosis.ok,
            -SEVERITY_ORDER[
                diagnosis.severity
            ],
            diagnosis.title,
        ),
    )

    counts = diagnosis_counts(
        diagnoses
    )

    return DoctorReport(
        diagnoses=diagnoses,
        critical=counts["critical"],
        error=counts["error"],
        warning=counts["warning"],
        healthy=counts["healthy"],
    )

def print_diagnoses(diagnoses: list[Diagnosis]) -> bool:
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
    parser = argparse.ArgumentParser(
        prog="betabox doctor"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "print the diagnostic report "
            "as JSON"
        ),
    )

    args = parser.parse_args(
        argv
    )

    config = DEFAULT_PLATFORM_CONFIG

    report = collect_doctor_report(
        config
    )

    if args.json:
        print(
            json.dumps(
                report.to_dict(),
                indent=2,
            )
        )
    else:
        print_diagnoses(
            report.diagnoses
        )

    return 0 if report.ok else 1


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
