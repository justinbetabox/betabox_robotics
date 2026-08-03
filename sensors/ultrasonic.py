from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING, ClassVar, Self, TypeAlias, cast

from betabox_robotics.hardware import (
    DigitalPin,
    HardwareError,
    Pin,
    PinMode,
    Pull,
)

from .exceptions import (
    UltrasonicError,
    UltrasonicReadError,
    UltrasonicTimeoutError,
)
from .types import UltrasonicReading

if TYPE_CHECKING:
    from betabox_robotics.robots.config import (
        UltrasonicConfig,
    )


PinInput: TypeAlias = Pin | DigitalPin | str | int


class Ultrasonic:
    """
    Ultrasonic distance sensor.

    Uses one trigger pin and one echo pin. Distance is returned in
    centimeters.

    The sensor owns both Pin objects, including Pin instances supplied
    by the caller, and closes them when the sensor is closed.
    """

    SOUND_SPEED_M_S: ClassVar[float] = 343.3
    TRIGGER_SETTLE_SECONDS: ClassVar[float] = 0.001
    TRIGGER_PULSE_SECONDS: ClassVar[float] = 0.00001

    def __init__(
        self,
        trigger: PinInput,
        echo: PinInput,
        *,
        timeout: float = 0.02,
    ) -> None:
        timeout_value = self._require_finite_number(
            timeout,
            name="timeout",
        )

        if timeout_value <= 0:
            raise UltrasonicError("timeout must be greater than 0")

        self.timeout = timeout_value

        self.trigger: Pin | None = None
        self.echo: Pin | None = None
        self._closed = False

        try:
            trigger_pin = self._make_output_pin(trigger)

            echo_pin = self._make_input_pin(echo)

            self.trigger = trigger_pin
            self.echo = echo_pin

            if trigger_pin.pin_number == echo_pin.pin_number:
                raise UltrasonicError("trigger and echo must use different GPIO pins")

            # Begin in a known, inactive trigger state.
            trigger_pin.off()

        except (
            HardwareError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ):
            self._close_constructed_pins()
            self._closed = True
            raise

    @staticmethod
    def _require_finite_number(
        value: object,
        *,
        name: str,
    ) -> float:
        if isinstance(value, bool) or not isinstance(
            value,
            int | float,
        ):
            raise TypeError(f"{name} must be a number")

        result = float(value)

        if not math.isfinite(result):
            raise ValueError(f"{name} must be finite")

        return result

    @staticmethod
    def _require_positive_samples(
        samples: object,
    ) -> int:
        if isinstance(samples, bool) or not isinstance(
            samples,
            int,
        ):
            raise TypeError("samples must be an integer")

        if samples <= 0:
            raise UltrasonicError("samples must be greater than 0")

        return samples

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def trigger_pin(self) -> Pin:
        pin = self.trigger

        if pin is None:
            raise UltrasonicError("ultrasonic trigger pin is closed")

        return pin

    @property
    def echo_pin(self) -> Pin:
        pin = self.echo

        if pin is None:
            raise UltrasonicError("ultrasonic echo pin is closed")

        return pin

    def _require_open(self) -> None:
        if self._closed:
            raise UltrasonicError("ultrasonic sensor is closed")

    @classmethod
    def default(
        cls,
        config: UltrasonicConfig,
    ) -> Self:
        return cls(
            trigger=config.trigger,
            echo=config.echo,
            timeout=config.timeout,
        )

    @staticmethod
    def _make_output_pin(
        pin: PinInput,
    ) -> Pin:
        if isinstance(
            pin,
            Pin,
        ):
            existing_pin = cast(
                Pin,
                pin,
            )

            existing_pin.output()

            return existing_pin

        return Pin(
            pin,
            mode=PinMode.OUT,
        )

    @staticmethod
    def _make_input_pin(
        pin: PinInput,
    ) -> Pin:
        if isinstance(
            pin,
            Pin,
        ):
            existing_pin = cast(
                Pin,
                pin,
            )

            existing_pin.input(
                pull=Pull.DOWN,
            )

            return existing_pin

        return Pin(
            pin,
            mode=PinMode.IN,
            pull=Pull.DOWN,
        )

    def _wait_for_echo_state(
        self,
        expected: int,
        *,
        timeout_message: str,
    ) -> float:
        deadline = time.monotonic() + self.timeout

        while self.echo_pin.read() != expected:
            now = time.monotonic()

            if now >= deadline:
                raise UltrasonicTimeoutError(timeout_message)

        return time.monotonic()

    def _read_once(self) -> float:
        self._require_open()

        trigger = self.trigger_pin

        trigger.off()
        time.sleep(self.TRIGGER_SETTLE_SECONDS)

        trigger.on()
        time.sleep(self.TRIGGER_PULSE_SECONDS)
        trigger.off()

        pulse_start = self._wait_for_echo_state(
            1,
            timeout_message=("timed out waiting for ultrasonic echo to start"),
        )

        pulse_end = self._wait_for_echo_state(
            0,
            timeout_message=("timed out waiting for ultrasonic echo to end"),
        )

        duration = pulse_end - pulse_start

        if duration <= 0:
            raise UltrasonicReadError("invalid ultrasonic pulse duration")

        return round(
            (duration * self.SOUND_SPEED_M_S / 2 * 100),
            2,
        )

    def distance(
        self,
        samples: int = 10,
    ) -> float:
        self._require_open()

        sample_count = self._require_positive_samples(samples)

        last_error: UltrasonicTimeoutError | UltrasonicReadError | None = None

        for _ in range(sample_count):
            try:
                return self._read_once()

            except (
                UltrasonicTimeoutError,
                UltrasonicReadError,
            ) as exc:
                last_error = exc

        message = f"no valid ultrasonic reading after {sample_count} attempts"

        if isinstance(
            last_error,
            UltrasonicReadError,
        ):
            raise UltrasonicReadError(message) from last_error

        raise UltrasonicTimeoutError(message) from last_error

    def read(
        self,
        times: int = 10,
    ) -> float:
        """
        Compatibility API.

        Returns distance in centimeters, -1 for a timeout, or -2 for an
        invalid reading. New code should use distance(), which raises a
        typed UltrasonicError.
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
        sample_count = self._require_positive_samples(samples)

        return UltrasonicReading(
            distance_cm=self.distance(samples=sample_count),
            samples_requested=sample_count,
        )

    def _close_constructed_pins(
        self,
    ) -> None:
        for pin in (
            self.echo,
            self.trigger,
        ):
            if pin is None:
                continue

            try:
                pin.close()
            except (
                HardwareError,
                OSError,
                RuntimeError,
            ):
                pass

        self.echo = None
        self.trigger = None

    def close(self) -> None:
        if self._closed:
            return

        first_error: HardwareError | OSError | RuntimeError | None = None

        try:
            for pin in (
                self.echo,
                self.trigger,
            ):
                if pin is None:
                    continue

                try:
                    pin.close()
                except (
                    HardwareError,
                    OSError,
                    RuntimeError,
                ) as exc:
                    if first_error is None:
                        first_error = exc

        finally:
            self.echo = None
            self.trigger = None
            self._closed = True

        if first_error is not None:
            raise first_error

    def deinit(self) -> None:
        self.close()

    def __enter__(self) -> Self:
        self._require_open()
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()
