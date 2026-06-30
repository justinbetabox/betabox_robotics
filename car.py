from .audio import Audio
from .drive import Drive
from .sensors import Sensors
from .system import System
from .vision import Vision


class Car:
    """
    Main interface to a Betabox robotic car.
    """

    def __init__(self):
        self.drive = Drive()
        self.sensors = Sensors()
        self.vision = Vision()
        self.audio = Audio()
        self.system = System()
