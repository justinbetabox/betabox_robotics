#!/usr/bin/env python3

from time import sleep

from betabox_robotics.camera import CameraMount
from betabox_robotics.robots import BETABOX_CAR


def main() -> None:
    print()
    print("Betabox Camera Mount Demo")
    print("=========================")
    print()

    with CameraMount.default(
        BETABOX_CAR.camera_mount
    ) as camera:

        print("Center")
        camera.center()
        sleep(1)

        print("Pan left")
        camera.pan(-30)
        sleep(1)

        print("Pan right")
        camera.pan(30)
        sleep(1)

        print("Tilt down")
        camera.tilt(-20)
        sleep(1)

        print("Tilt up")
        camera.tilt(25)
        sleep(1)

        print("Diagonal")
        camera.look(
            pan=20,
            tilt=-10,
        )
        sleep(1)

        print("Center")
        camera.center()
        sleep(1)

    print()
    print("Camera mount demo complete.")


if __name__ == "__main__":
    main()
