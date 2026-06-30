#!/usr/bin/env python3

from time import sleep

from betabox_car.drive import Drive

with Drive.default() as drive:
    drive.center()
    sleep(1)

    drive.forward(40)
    sleep(2)

    drive.stop()
    sleep(1)

    drive.left(20)
    sleep(1)

    drive.forward(30)
    sleep(2)

    drive.stop()
    drive.center()
