from __future__ import annotations

import argparse
from dataclasses import dataclass

from betabox_robotics.services.managed import MANAGED_SERVICES
from betabox_robotics.services.status import collect_status
from betabox_robotics.services.verify import CheckResult, collect_checks
from betabox_robotics.services.hardware_status import RobotHardwareStatus
from betabox_robotics.services.status import StatusReport, collect_status


@dataclass(frozen=True)
class Diagnosis:
    title: str
    ok: bool
    message: str
    suggestions: list[str]


def result_map(results: list[CheckResult]) -> dict[str, CheckResult]:
    return {result.name: result for result in results}


def diagnose_i2c(results: dict[str, CheckResult]) -> Diagnosis:
    device = results.get("hardware:i2c")
    scan = results.get("hardware:i2cdetect")

    ok = bool(device and device.ok and scan and scan.ok)

    suggestions = [
        "Verify /boot/firmware/config.txt contains dtparam=i2c_arm=on.",
        "Reboot after enabling I²C.",
        "Check that the Robot HAT is seated correctly.",
        "Run: i2cdetect -y 1",
    ]

    return Diagnosis(
        title="I²C",
        ok=ok,
        message="I²C is available." if ok else "I²C is not fully available.",
        suggestions=[] if ok else suggestions,
    )


def diagnose_camera(results: dict[str, CheckResult]) -> Diagnosis:
    camera = results.get("camera:picamera2")
    ok = bool(camera and camera.ok)

    suggestions = [
        "Verify the camera ribbon cable is connected correctly.",
        "Reboot if the camera was recently enabled or connected.",
        "Run: python -c \"from picamera2 import Picamera2; print('picamera2 ok')\"",
        "Check whether another process is using the camera.",
    ]

    return Diagnosis(
        title="Camera",
        ok=ok,
        message="Picamera2 is available." if ok else "Picamera2 is unavailable.",
        suggestions=[] if ok else suggestions,
    )


def diagnose_audio(results: dict[str, CheckResult]) -> Diagnosis:
    hifiberry = results.get("audio:hifiberry")
    speech = results.get("audio:speech_backend")

    ok = bool(hifiberry and hifiberry.ok and speech and speech.ok)

    suggestions = [
        "Verify /boot/firmware/config.txt contains dtoverlay=hifiberry-dac.",
        "Verify /boot/firmware/config.txt contains dtoverlay=i2s-mmap.",
        "Reboot after changing audio overlays.",
        "Run: aplay -l",
        "Verify a speech backend is installed, such as espeak-ng or pico2wave.",
        "Do not keep GPIO20 high at boot; the SDK controls the speaker amplifier during playback.",
    ]

    return Diagnosis(
        title="Audio",
        ok=ok,
        message="Audio platform is available."
        if ok
        else "Audio platform is not fully available.",
        suggestions=[] if ok else suggestions,
    )


def diagnose_media(results: dict[str, CheckResult]) -> Diagnosis:
    required = [
        "media:pictures",
        "media:videos",
        "media:sounds",
    ]

    missing = [
        name for name in required if not (results.get(name) and results[name].ok)
    ]

    ok = not missing

    suggestions = [
        "Run the deployment installer again.",
        "Create missing media folders under ~/media.",
        "Expected folders: ~/media/pictures, ~/media/videos, ~/media/sounds.",
    ]

    return Diagnosis(
        title="Media",
        ok=ok,
        message="Media folders are available."
        if ok
        else f"Missing media paths: {', '.join(missing)}",
        suggestions=[] if ok else suggestions,
    )


def diagnose_services(status: StatusReport) -> Diagnosis:

    failed = [
        managed.title
        for managed in MANAGED_SERVICES.values()
        if status.services.get(managed.unit) == "failed"
    ]

    not_ready = [
        f"{managed.title} ({status.services.get(managed.unit, 'unknown')})"
        for managed in MANAGED_SERVICES.values()
        if status.services.get(managed.unit, "unknown")
        not in ("active", "inactive", "not-installed")
    ]

    ok = not failed

    suggestions = [
        "Run: betabox services",
        "Run: betabox logs <service>",
        "Restart a failed service with: sudo systemctl restart <service>",
    ]

    message = "No failed managed services detected."

    if failed:
        message = "Failed services detected: " + ", ".join(failed)
    elif not_ready:
        message = "Some services need attention: " + ", ".join(not_ready)

    return Diagnosis(
        title="Services",
        ok=ok,
        message=message,
        suggestions=[] if ok else suggestions,
    )


def diagnose_jupyterhub(
    results: dict[str, CheckResult],
    status: StatusReport,
) -> Diagnosis:
    proxy = results.get("jupyterhub:proxy")
    service_state = status.services.get("jupyterhub.service", "unknown")

    ok = bool(proxy and proxy.ok and service_state == "active")

    suggestions = [
        "Install Node.js and npm: sudo apt install -y nodejs npm",
        "Install the proxy: sudo npm install -g configurable-http-proxy",
        "Restart JupyterHub: sudo systemctl restart jupyterhub.service",
        "Check logs: betabox logs jupyterhub --journal-only",
        "Check health: curl -I http://127.0.0.1:8000/hub/health",
    ]

    if ok:
        message = "JupyterHub service and proxy are available."
    elif not (proxy and proxy.ok):
        message = "JupyterHub proxy is missing."
    elif service_state != "active":
        message = f"JupyterHub service is {service_state}."
    else:
        message = "JupyterHub is not fully available."

    return Diagnosis(
        title="JupyterHub",
        ok=ok,
        message=message,
        suggestions=[] if ok else suggestions,
    )

def diagnose_robot_hardware(hardware: RobotHardwareStatus) -> Diagnosis:
    ok = hardware.robot_available and hardware.i2c.available

    suggestions = [
        "Verify /boot/firmware/config.txt contains dtparam=i2c_arm=on.",
        "Run: i2cdetect -y 1",
        "Check that the Robot HAT is seated correctly.",
        "Check the Robot HAT power and cable connections.",
    ]

    if ok:
        message = "Robot hardware and I²C bus are available."
    elif hardware.robot_error:
        message = f"Robot hardware is unavailable: {hardware.robot_error}"
    elif not hardware.i2c.available:
        message = "The I²C bus is unavailable."
    else:
        message = "Robot hardware is unavailable."

    return Diagnosis(
        title="Robot Hardware",
        ok=ok,
        message=message,
        suggestions=[] if ok else suggestions,
    )


def diagnose_battery(hardware: RobotHardwareStatus) -> Diagnosis:
    battery = hardware.battery

    if not battery.available or battery.voltage is None:
        return Diagnosis(
            title="Battery",
            ok=False,
            message=battery.error or "Battery voltage is unavailable.",
            suggestions=[
                "Check the battery connection.",
                "Check the Robot HAT power connection.",
                "Run: betabox status",
                "Run: betabox verify",
            ],
        )

    critical = battery.state == "critical"

    if critical:
        message = (
            f"Battery voltage is critical: {battery.voltage:.2f} V."
        )
    elif battery.state == "low":
        message = f"Battery voltage is low: {battery.voltage:.2f} V."
    else:
        message = (
            f"Battery voltage is healthy: {battery.voltage:.2f} V."
        )

    return Diagnosis(
        title="Battery",
        ok=not critical,
        message=message,
        suggestions=(
            [
                "Stop driving the robot.",
                "Recharge or replace the battery.",
                "Check the battery connector.",
            ]
            if critical
            else []
        ),
    )


def diagnose_grayscale(hardware: RobotHardwareStatus) -> Diagnosis:
    sensors = hardware.sensors
    ok = sensors.grayscale_available

    if ok:
        values = sensors.grayscale_values or []
        message = "Grayscale sensor is available."

        if values:
            message += " Values: " + ", ".join(str(value) for value in values)
    else:
        message = sensors.error or "Grayscale sensor is unavailable."

    return Diagnosis(
        title="Grayscale",
        ok=ok,
        message=message,
        suggestions=(
            []
            if ok
            else [
                "Check the grayscale sensor cable.",
                "Check the Robot HAT connection.",
                "Run the grayscale validation test.",
            ]
        ),
    )


def diagnose_audio_hardware(hardware: RobotHardwareStatus) -> Diagnosis:
    audio = hardware.audio
    ok = audio.available

    return Diagnosis(
        title="Audio Hardware",
        ok=ok,
        message=(
            f"Audio device is available: {audio.device}."
            if ok
            else audio.error or "Audio device is unavailable."
        ),
        suggestions=(
            []
            if ok
            else [
                "Run: aplay -l",
                "Verify dtoverlay=hifiberry-dac is configured.",
                "Reboot after changing audio overlays.",
            ]
        ),
    )


def diagnose_vision_hardware(hardware: RobotHardwareStatus) -> Diagnosis:
    vision = hardware.vision

    ok = (
        vision.service_available
        and vision.running
        and vision.camera_running
        and vision.camera_has_frame
    )

    if ok:
        message = "Vision service and camera pipeline are healthy."
    elif not vision.service_available:
        message = vision.error or "Vision service is unavailable."
    elif not vision.running:
        message = "Vision service is not running."
    elif not vision.camera_running:
        message = "Vision service is running, but the camera is stopped."
    elif not vision.camera_has_frame:
        message = "Vision service is running, but no camera frame is available."
    else:
        message = "Vision platform is degraded."

    return Diagnosis(
        title="Vision Hardware",
        ok=ok,
        message=message,
        suggestions=(
            []
            if ok
            else [
                "Run: betabox services",
                "Run: betabox logs video --journal-only",
                "Restart Vision: sudo systemctl restart betabox-video.service",
                "Check the camera ribbon cable.",
            ]
        ),
    )

def collect_diagnoses(*, include_robot: bool = True) -> list[Diagnosis]:
    checks = result_map(collect_checks(include_robot=False))
    status = collect_status()
    hardware = status.hardware

    diagnoses = [
        diagnose_i2c(checks),
        diagnose_camera(checks),
        diagnose_audio(checks),
        diagnose_jupyterhub(checks, status),
        diagnose_media(checks),
        diagnose_services(status),
        diagnose_robot_hardware(hardware),
        diagnose_battery(hardware),
        diagnose_grayscale(hardware),
        diagnose_audio_hardware(hardware),
        diagnose_vision_hardware(hardware),
    ]

    return diagnoses


def print_diagnoses(diagnoses: list[Diagnosis]) -> bool:
    print()
    print("Betabox Doctor")
    print("==============")
    print()

    all_ok = True

    for diagnosis in diagnoses:
        status = "OK" if diagnosis.ok else "ISSUE"
        print(f"[{status}] {diagnosis.title}")
        print(f"      {diagnosis.message}")

        if diagnosis.suggestions:
            print()
            print("      Suggested actions:")
            for suggestion in diagnosis.suggestions:
                print(f"      - {suggestion}")

        print()

        if not diagnosis.ok:
            all_ok = False

    if all_ok:
        print("No major platform issues detected.")
    else:
        print("One or more issues were detected.")

    print()
    return all_ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="betabox doctor")

    args = parser.parse_args(argv)

    diagnoses = collect_diagnoses()
    return 0 if print_diagnoses(diagnoses) else 1


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
