from __future__ import annotations

import time
from typing import TYPE_CHECKING, Self, TypeAlias, cast

from betabox_robotics.hardware import (
    DigitalPin,
    Pin,
)

from .exceptions import (
    UltrasonicError,
    UltrasonicReadError,
    UltrasonicTimeoutError,
)
from .types import UltrasonicReading

if TYPE_CHECKING:
    from betabox_robotics.robots.config import UltrasonicConfig

PinInput: TypeAlias = Pin | DigitalPin | str | int

class Ultrasonic:
    """
    Ultrasonic distance sensor.

    Uses one trigger pin and one echo pin.
    Distance is returned in centimeters.
    """

    SOUND_SPEED_M_S = 343.3

    def __init__(
        self,
        trigger: PinInput,
        echo: PinInput,
        *,
        timeout: float = 0.02,
    ) -> None:
        if timeout <= 0:
            raise UltrasonicError("timeout must be greater than 0")

        self.timeout = float(timeout)

        self.trigger = self._make_output_pin(trigger)
        self.echo = self._make_input_pin(echo)

        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed


    def _require_open(self) -> None:
        if self._closed:
            raise UltrasonicError(
                "ultrasonic sensor is closed"
            )

    @classmethod
    def default(cls, config: "UltrasonicConfig") -> "Ultrasonic":
        return cls(
            trigger=config.trigger,
            echo=config.echo,
            timeout=config.timeout,
        )

    def _make_output_pin(self, pin: PinInput) -> Pin:
        if isinstance(pin, Pin):
            pin = cast(Pin, pin)
            pin.output()
            return pin

        return Pin(pin, mode=Pin.OUT)

    def _make_input_pin(self, pin: PinInput) -> Pin:
        if isinstance(pin, Pin):
            pin = cast(Pin, pin)
            pin.input(pull=Pin.PULL_DOWN)
            return pin

        return Pin(pin, mode=Pin.IN, pull=Pin.PULL_DOWN)

    def _read_once(self) -> float:
        self._require_open()

        self.trigger.off()
        time.sleep(0.001)

        self.trigger.on()
        time.sleep(0.00001)
        self.trigger.off()

        timeout_start = time.monotonic()

        while self.echo.read() == 0:
            if time.monotonic() - timeout_start > self.timeout:
                raise UltrasonicTimeoutError(
                    "timed out waiting for ultrasonic echo to start"
                )

        pulse_start = time.monotonic()

        while self.echo.read() == 1:
            if time.monotonic() - pulse_start > self.timeout:
                raise UltrasonicTimeoutError(
                    "timed out waiting for ultrasonic echo to end"
                )

        pulse_end = time.monotonic()

        duration = pulse_end - pulse_start

        if duration <= 0:
            raise UltrasonicReadError(
                "invalid ultrasonic pulse duration"
            )

        return round(
            duration * self.SOUND_SPEED_M_S / 2 * 100,
            2,
        )

    def distance(self, samples: int = 10) -> float:
        self._require_open()

        if samples <= 0:
            raise UltrasonicError(
                "samples must be greater than 0"
            )

        last_error: UltrasonicError | None = None

        for _ in range(samples):
            try:
                return self._read_once()
            except UltrasonicError as exc:
                last_error = exc

        if isinstance(last_error, UltrasonicReadError):
            raise UltrasonicReadError(
                f"no valid ultrasonic reading after {samples} attempts"
            ) from last_error

        raise UltrasonicTimeoutError(
            f"no valid ultrasonic reading after {samples} attempts"
        ) from last_error

    def read(self, times: int = 10) -> float:
        """
        Compatibility API.

        Returns distance in centimeters, or -1 when a valid reading
        cannot be obtained. New code should use distance(), which raises
        a typed UltrasonicError instead.
        """
        try:
            return self.distance(samples=times)
        except UltrasonicTimeoutError:
            return -1
        except UltrasonicReadError:
            return -2

    def reading(
        self,
        samples: int = 10,
    ) -> UltrasonicReading:
        return UltrasonicReading(
            distance_cm=self.distance(samples=samples),
            samples_requested=samples,
        )

    def close(self) -> None:
        if self._closed:
            return

        try:
            self.trigger.close()
        finally:
            try:
                self.echo.close()
            finally:
                self._closed = True

    def __enter__(self) -> Self:
        self._require_open()
        return self

    def deinit(self) -> None:
        self.close()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
