from betabox_car.audio import Audio
from betabox_car.drive import Drive
from betabox_car.robots import BETABOX_CAR
from betabox_car.sensors import Sensors
from betabox_car.system import System
from betabox_car.vision import Vision

from .base import RobotBase


class BetaboxCar(RobotBase):
    """
    Betabox Car robot platform.
    """

    def __init__(self):
        self.drive = Drive.default(BETABOX_CAR)
        self.sensors = Sensors.default(BETABOX_CAR)
        self.vision = Vision.default(BETABOX_CAR)
        self.audio = Audio.default(BETABOX_CAR)
        self.system = System.default(BETABOX_CAR)

    def close(self) -> None:
        for subsystem in (
            self.audio,
            self.vision,
            self.drive,
            self.sensors,
            self.system,
        ):
            close = getattr(subsystem, "close", None)

            if callable(close):
                close()
