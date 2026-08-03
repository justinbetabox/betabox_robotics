#!/usr/bin/env python3
"""
Betabox Camera Mount developer demo.

Exercises the two-axis camera mount using the CameraMount subsystem.

This demo validates:

- CameraMount.default();
- pan/tilt movement;
- combined look() movement;
- logical angle reporting;
- configured limits;
- configured offsets;
- smooth and immediate movement;
- status reporting;
- context-managed cleanup.

WARNING:
Ensure the camera and servo wiring have enough clearance before running
this demo. The mount will move through much of its configured range.
"""

from __future__ import annotations

from time import sleep

from betabox_robotics.camera import (
    CameraMount,
    CameraMountError,
)
from betabox_robotics.hardware import HardwareError
from betabox_robotics.robots import BETABOX_CAR

STEP_DELAY = 1.0


def print_status(
    label: str,
    mount: CameraMount,
) -> None:
    status = mount.status()

    print()
    print(label)
    print("-" * len(label))
    print(f"Pan:          {status.pan}")
    print(f"Tilt:         {status.tilt}")
    print(f"Pan offset:   {status.pan_offset}")
    print(f"Tilt offset:  {status.tilt_offset}")
    print(f"Pan range:    {status.pan_min} to {status.pan_max}")
    print(f"Tilt range:   {status.tilt_min} to {status.tilt_max}")
    print(f"Closed:       {mount.closed}")


def pause() -> None:
    sleep(STEP_DELAY)


def main() -> int:
    print()
    print("Betabox Camera Mount demo")
    print("=========================")
    print()
    print("WARNING: Ensure the camera has clearance before continuing.")
    print("Press Ctrl+C at any time to stop the demo.")

    mount: CameraMount | None = None

    try:
        camera = CameraMount.default(
            BETABOX_CAR.camera_mount,
        )
        mount = camera

        with camera:
            print_status(
                "Initial state",
                camera,
            )

            print()
            print("Centering...")
            camera.center()
            pause()

            print_status(
                "Centered",
                camera,
            )

            print()
            print("Pan left...")
            camera.pan(-30)
            pause()

            print_status(
                "Pan left",
                camera,
            )

            print()
            print("Pan right...")
            camera.pan(30)
            pause()

            print_status(
                "Pan right",
                camera,
            )

            print()
            print("Tilt down...")
            camera.tilt(-20)
            pause()

            print_status(
                "Tilt down",
                camera,
            )

            print()
            print("Tilt up...")
            camera.tilt(25)
            pause()

            print_status(
                "Tilt up",
                camera,
            )

            print()
            print("Diagonal movement...")
            camera.look(
                pan=20,
                tilt=-10,
            )
            pause()

            print_status(
                "Diagonal",
                camera,
            )

            print()
            print("Immediate center...")
            camera.center(
                smooth=False,
            )
            pause()

            print_status(
                "Final state",
                camera,
            )

        print()
        print(f"Closed after context exit: {camera.closed}")

    except KeyboardInterrupt:
        print()
        print("Camera mount demo interrupted.")
        return 130

    except CameraMountError as exc:
        print()
        print(f"Camera mount demo failed: {exc}")
        return 1

    except (
        HardwareError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        print()
        print(f"Camera mount demo failed: {type(exc).__name__}: {exc}")
        return 1

    finally:
        if mount is not None and not mount.closed:
            mount.close()

    print()
    print("Camera mount demo complete.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
