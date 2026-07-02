from typing import List, Optional, Tuple

from betabox_car.hardware import ADC, HardwareError


class GrayscaleError(HardwareError):
    """Raised when a grayscale sensor operation fails."""


class Grayscale:
    """
    Three-channel grayscale sensor.

    Channels are ordered left, middle, right.
    """

    LEFT = 0
    MIDDLE = 1
    RIGHT = 2

    REFERENCE_DEFAULT = [1000, 1000, 1000]

    def __init__(
        self,
        left: ADC,
        middle: ADC,
        right: ADC,
        reference: Optional[List[int]] = None,
    ) -> None:
        self.channels = (
            left,
            middle,
            right,
        )

        self._reference = (
            reference if reference is not None else list(self.REFERENCE_DEFAULT)
        )
        self._floor: Optional[List[float]] = None
        self._line: Optional[List[float]] = None

    def read(self, channel: Optional[int] = None) -> List[int]:
        if channel is None:
            return [adc.read() for adc in self.channels]

        self._validate_channel(channel)
        return [self.channels[channel].read()]

    def reference(self, values: Optional[List[int]] = None) -> List[int]:
        """
        Legacy reference threshold API.
        """
        if values is not None:
            if not isinstance(values, list) or len(values) != 3:
                raise GrayscaleError("reference values must be a 3-element list")

            self._reference = values

        return self._reference

    def set_calibration(self, floor: List[float], line: List[float]) -> None:
        if len(floor) != 3 or len(line) != 3:
            raise GrayscaleError("floor and line must each contain 3 values")

        self._floor = [float(value) for value in floor]
        self._line = [float(value) for value in line]

    def get_calibration(self) -> Tuple[Optional[List[float]], Optional[List[float]]]:
        return self._floor, self._line

    def normalized(self, raw: Optional[List[int]] = None) -> List[float]:
        if self._floor is None or self._line is None:
            raise GrayscaleError(
                "calibration not set. Call set_calibration(floor, line) first."
            )

        values = raw if raw is not None else self.read()

        if len(values) != 3:
            raise GrayscaleError("raw values must contain 3 readings")

        normalized_values = []

        for index, value in enumerate(values):
            floor = self._floor[index]
            line = self._line[index]

            if line > floor:
                span = max(line - floor, 1e-6)
                normalized = (value - floor) / span
            else:
                span = max(floor - line, 1e-6)
                normalized = (floor - value) / span

            normalized = self._clamp(normalized, 0.0, 1.0)
            normalized_values.append(normalized)

        return normalized_values

    def status(
        self,
        raw: Optional[List[int]] = None,
        threshold: float = 0.5,
    ) -> List[int]:
        """
        Return 0 for floor and 1 for line.

        If floor/line calibration is available, normalized values are used.
        Otherwise, legacy reference thresholds are used.
        """
        if self._floor is not None and self._line is not None:
            return [1 if value > threshold else 0 for value in self.normalized(raw)]

        values = raw if raw is not None else self.read()

        if len(values) != 3:
            raise GrayscaleError("raw values must contain 3 readings")

        return [
            0 if value > self._reference[index] else 1
            for index, value in enumerate(values)
        ]

    def read_status(
        self,
        datas: Optional[List[int]] = None,
        threshold: float = 0.5,
    ) -> List[int]:
        """
        Compatibility alias for old API.
        """
        return self.status(raw=datas, threshold=threshold)

    def get_grayscale_normalized(self) -> List[float]:
        """
        Compatibility alias for old API.
        """
        return self.normalized()

    def close(self) -> None:
        for adc in self.channels:
            adc.close()

    def deinit(self) -> None:
        self.close()

    def _validate_channel(self, channel: int) -> None:
        if channel not in (self.LEFT, self.MIDDLE, self.RIGHT):
            raise GrayscaleError(
                "channel must be Grayscale.LEFT, Grayscale.MIDDLE, or Grayscale.RIGHT"
            )

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
