import time
from typing import Union

from betabox_car.hardware import DigitalPin, HardwareError, Pin
from betabox_car.robots import ROBOT


class UltrasonicError(HardwareError):
    """Raised when an ultrasonic sensor operation fails."""


class Ultrasonic:
    """
    Ultrasonic distance sensor.

    Uses one trigger pin and one echo pin.
    Distance is returned in centimeters.
    """

    SOUND_SPEED_M_S = 343.3

    def __init__(
        self,
        trigger: Union[Pin, DigitalPin, str, int] = ROBOT.ultrasonic.trigger,
        echo: Union[Pin, DigitalPin, str, int] = ROBOT.ultrasonic.echo,
        *,
        timeout: float = 0.02,
    ) -> None:
        if timeout <= 0:
            raise UltrasonicError("timeout must be greater than 0")

        self.timeout = float(timeout)

        self.trigger = self._make_output_pin(trigger)
        self.echo = self._make_input_pin(echo)

    def _make_output_pin(self, pin) -> Pin:
        if isinstance(pin, Pin):
            pin.output()
            return pin

        return Pin(pin, mode=Pin.OUT)

    def _make_input_pin(self, pin) -> Pin:
        if isinstance(pin, Pin):
            pin.input(pull=Pin.PULL_DOWN)
            return pin

        return Pin(pin, mode=Pin.IN, pull=Pin.PULL_DOWN)

    def _read_once(self) -> float:
        self.trigger.off()
        time.sleep(0.001)

        self.trigger.on()
        time.sleep(0.00001)
        self.trigger.off()

        pulse_start = 0.0
        pulse_end = 0.0
        timeout_start = time.time()

        while self.echo.read() == 0:
            pulse_start = time.time()

            if pulse_start - timeout_start > self.timeout:
                return -1

        while self.echo.read() == 1:
            pulse_end = time.time()

            if pulse_end - timeout_start > self.timeout:
                return -1

        if pulse_start == 0 or pulse_end == 0:
            return -2

        duration = pulse_end - pulse_start
        distance_cm = round(duration * self.SOUND_SPEED_M_S / 2 * 100, 2)

        return distance_cm

    def distance(self, samples: int = 10) -> float:
        if samples <= 0:
            raise UltrasonicError("samples must be greater than 0")

        for _ in range(samples):
            value = self._read_once()

            if value != -1:
                return value

        return -1

    def read(self, times: int = 10) -> float:
        """
        Compatibility alias for old API.
        """
        return self.distance(samples=times)

    def close(self) -> None:
        if hasattr(self, "trigger"):
            self.trigger.close()
        if hasattr(self, "echo"):
            self.echo.close()

    def deinit(self) -> None:
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
