from .battery import Battery
from .grayscale import Grayscale
from .ultrasonic import Ultrasonic


class Sensors:
    """
    Sensor subsystem.
    """

    def __init__(self):
        self.ultrasonic = Ultrasonic()
        self.grayscale = Grayscale()
        self.battery = Battery()

    def close(self):
        self.ultrasonic.close()
        self.grayscale.close()
        self.battery.close()

    def deinit(self):
        self.close()
