from .battery import Battery
from .grayscale import Grayscale
from .ultrasonic import Ultrasonic


class Sensors:
    """
    Sensor subsystem.
    """

    def __init__(
        self,
        *,
        ultrasonic: Ultrasonic,
        grayscale: Grayscale,
        battery: Battery,
    ) -> None:
        self.ultrasonic = ultrasonic
        self.grayscale = grayscale
        self.battery = battery

    @classmethod
    def default(cls, robot_config) -> "Sensors":
        return cls(
            ultrasonic=Ultrasonic.default(robot_config),
            grayscale=Grayscale.default(robot_config),
            battery=Battery.default(robot_config),
        )

    def close(self) -> None:
        self.ultrasonic.close()
        self.grayscale.close()
        self.battery.close()

    def deinit(self) -> None:
        self.close()

    def __enter__(self) -> "Sensors":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
