#!/usr/bin/env python3

from time import sleep

from betabox_car.drive import Drive

drive = Drive.default()

try:
    print("Center steering")
    drive.center()
    sleep(1)

    print("Forward")
    drive.forward(30)
    sleep(2)

    print("Stop")
    drive.stop()
    sleep(1)

    print("Backward")
    drive.backward(30)
    sleep(2)

    print("Stop")
    drive.stop()
    sleep(1)

    print("Left")
    drive.left(20)
    sleep(1)

    print("Right")
    drive.right(20)
    sleep(1)

    print("Center")
    drive.center()

finally:
    drive.close()

print("Drive test complete.")
