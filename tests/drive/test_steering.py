#!/usr/bin/env python3

from time import sleep

from betabox_car.drive import Drive

drive = Drive.default()

try:
    print("\nSteering servo test")
    print("Only the steering servo should move.")
    print("Camera pan/tilt servos should NOT move.\n")

    print("Center")
    drive.center()
    sleep(2)

    print("Left 20")
    drive.left(20)
    sleep(2)

    print("Right 20")
    drive.right(20)
    sleep(2)

    print("Center")
    drive.center()
    sleep(2)

finally:
    drive.close()

print("Steering test complete.")
