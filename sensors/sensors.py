from betabox_car.hardware import ADC

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
    ):
        self.ultrasonic = ultrasonic
        self.grayscale = grayscale
        self.battery = battery

    @classmethod
    def default(cls, robot_config):
        return cls(
            ultrasonic=Ultrasonic(
                trigger=robot_config.ultrasonic.trigger,
                echo=robot_config.ultrasonic.echo,
            ),
            grayscale=Grayscale(
                left=ADC(robot_config.grayscale.left),
                middle=ADC(robot_config.grayscale.middle),
                right=ADC(robot_config.grayscale.right),
            ),
            battery=Battery(
                adc=ADC(robot_config.battery.channel),
                scale=robot_config.battery.scale,
                low_voltage=robot_config.battery.low_voltage,
                critical_voltage=robot_config.battery.critical_voltage,
            ),
        )

    def close(self):
        self.ultrasonic.close()
        self.grayscale.close()
        self.battery.close()

    def deinit(self):
        self.close()
