from __future__ import annotations

import argparse
from dataclasses import dataclass

from betabox_robotics.services.status import collect_status
from betabox_robotics.services.verify import CheckResult, collect_checks


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


def diagnose_services() -> Diagnosis:
    status = collect_status()
    inactive = [
        service
        for service, state in status.services.items()
        if state not in ("active", "inactive")
    ]

    failed = [
        service for service, state in status.services.items() if state == "failed"
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
    elif inactive:
        message = "Some services are not installed or inactive: " + ", ".join(inactive)

    return Diagnosis(
        title="Services",
        ok=ok,
        message=message,
        suggestions=[] if ok else suggestions,
    )


def diagnose_robot(results: dict[str, CheckResult]) -> Diagnosis:
    robot = results.get("robot:construct")
    ok = bool(robot and robot.ok)

    suggestions = [
        "Run: betabox verify",
        "Check I²C and Robot HAT connectivity.",
        "Check battery power.",
        "Review the exact robot construction error shown by betabox verify.",
    ]

    return Diagnosis(
        title="Robot",
        ok=ok,
        message="Robot object can be constructed."
        if ok
        else "Robot object could not be constructed.",
        suggestions=[] if ok else suggestions,
    )


def diagnose_jupyterhub(results: dict[str, CheckResult]) -> Diagnosis:
    proxy = results.get("jupyterhub:proxy")
    status = collect_status()
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


def collect_diagnoses(*, include_robot: bool = True) -> list[Diagnosis]:
    checks = result_map(collect_checks(include_robot=include_robot))

    diagnoses = [
        diagnose_i2c(checks),
        diagnose_camera(checks),
        diagnose_audio(checks),
        diagnose_jupyterhub(checks),
        diagnose_media(checks),
        diagnose_services(),
    ]

    if include_robot:
        diagnoses.append(diagnose_robot(checks))

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
    parser.add_argument(
        "--no-robot",
        action="store_true",
        help="Skip checks that construct the robot object",
    )

    args = parser.parse_args(argv)

    diagnoses = collect_diagnoses(include_robot=not args.no_robot)
    return 0 if print_diagnoses(diagnoses) else 1


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
