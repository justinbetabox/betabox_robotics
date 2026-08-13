from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from betabox_robotics.hardware import (
    HardwareError,
    Servo,
)

from .exceptions import CameraMountError

if TYPE_CHECKING:
    from betabox_robotics.robots.config import (
        CameraMountConfig,
    )


@dataclass(
    frozen=True,
    slots=True,
)
class CameraMountStatus:
    pan: float | None
    tilt: float | None

    pan_offset: float
    tilt_offset: float

    pan_min: float
    pan_max: float

    tilt_min: float
    tilt_max: float

    def to_dict(
        self,
    ) -> dict[str, float | None]:
        return {
            "pan": self.pan,
            "tilt": self.tilt,
            "pan_offset": self.pan_offset,
            "tilt_offset": self.tilt_offset,
            "pan_min": self.pan_min,
            "pan_max": self.pan_max,
            "tilt_min": self.tilt_min,
            "tilt_max": self.tilt_max,
        }


class CameraMount:
    """
    Reusable two-axis camera mount.

    Public pan and tilt values are logical mount angles in degrees.
    The mount owns both underlying Servo instances.
    """

    config: CameraMountConfig

    _pan_min: float
    _pan_max: float
    _tilt_min: float
    _tilt_max: float

    _pan_center: float
    _tilt_center: float

    _pan_servo: Servo | None
    _tilt_servo: Servo | None

    _pan: float | None
    _tilt: float | None

    _closed: bool

    def __init__(
        self,
        config: CameraMountConfig,
        *,
        pan_offset: float = 0.0,
        tilt_offset: float = 0.0,
    ) -> None:
        pan_min = self._require_finite_number(
            config.pan_min_angle,
            name="pan_min_angle",
        )
        pan_max = self._require_finite_number(
            config.pan_max_angle,
            name="pan_max_angle",
        )
        tilt_min = self._require_finite_number(
            config.tilt_min_angle,
            name="tilt_min_angle",
        )
        tilt_max = self._require_finite_number(
            config.tilt_max_angle,
            name="tilt_max_angle",
        )
        pan_center = self._require_finite_number(
            config.pan_center,
            name="pan_center",
        )
        tilt_center = self._require_finite_number(
            config.tilt_center,
            name="tilt_center",
        )
        pan_offset_value = self._require_finite_number(
            pan_offset,
            name="pan_offset",
        )
        tilt_offset_value = self._require_finite_number(
            tilt_offset,
            name="tilt_offset",
        )

        if pan_min >= pan_max:
            raise CameraMountError("pan_min_angle must be less than pan_max_angle")

        if tilt_min >= tilt_max:
            raise CameraMountError("tilt_min_angle must be less than tilt_max_angle")

        if not pan_min <= pan_center <= pan_max:
            raise CameraMountError("pan_center must be within the configured pan range")

        if not tilt_min <= tilt_center <= tilt_max:
            raise CameraMountError(
                "tilt_center must be within the configured tilt range"
            )

        self.config = config

        self._pan_min = pan_min
        self._pan_max = pan_max
        self._tilt_min = tilt_min
        self._tilt_max = tilt_max
        self._pan_center = pan_center
        self._tilt_center = tilt_center

        self._pan_servo = None
        self._tilt_servo = None

        self._pan = None
        self._tilt = None
        self._closed = False

        pan_servo_min, pan_servo_max = self._logical_limits_to_servo_limits(
            pan_min,
            pan_max,
            reversed=config.pan_reversed,
        )

        tilt_servo_min, tilt_servo_max = self._logical_limits_to_servo_limits(
            tilt_min,
            tilt_max,
            reversed=config.tilt_reversed,
        )

        try:
            self._pan_servo = Servo(
                config.pan_servo,
                min_angle=pan_servo_min,
                max_angle=pan_servo_max,
                offset=pan_offset_value,
            )

            self._tilt_servo = Servo(
                config.tilt_servo,
                min_angle=tilt_servo_min,
                max_angle=tilt_servo_max,
                offset=tilt_offset_value,
            )

        except (
            HardwareError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ):
            self._close_constructed_servos()
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
    def _logical_limits_to_servo_limits(
        minimum: float,
        maximum: float,
        *,
        reversed: bool,
    ) -> tuple[float, float]:
        if reversed:
            return (
                -maximum,
                -minimum,
            )

        return (
            minimum,
            maximum,
        )

    @staticmethod
    def _logical_to_servo_angle(
        angle: float,
        *,
        reversed: bool,
    ) -> float:
        return -angle if reversed else angle

    @staticmethod
    def _servo_to_logical_angle(
        angle: float,
        *,
        reversed: bool,
    ) -> float:
        return -angle if reversed else angle

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def pan_servo(self) -> Servo:
        servo = self._pan_servo

        if servo is None:
            raise CameraMountError("camera pan servo is closed")

        return servo

    @property
    def tilt_servo(self) -> Servo:
        servo = self._tilt_servo

        if servo is None:
            raise CameraMountError("camera tilt servo is closed")

        return servo

    @property
    def pan_angle(self) -> float | None:
        return self._pan

    @property
    def tilt_angle(self) -> float | None:
        return self._tilt

    @property
    def pan_offset(self) -> float:
        return self.pan_servo.offset

    @property
    def tilt_offset(self) -> float:
        return self.tilt_servo.offset

    @classmethod
    def default(
        cls,
        config: CameraMountConfig,
        *,
        pan_offset: float = 0.0,
        tilt_offset: float = 0.0,
    ) -> Self:
        return cls(
            config,
            pan_offset=pan_offset,
            tilt_offset=tilt_offset,
        )

    def look(
        self,
        *,
        pan: float | None = None,
        tilt: float | None = None,
        smooth: bool = True,
    ) -> None:
        self._require_open()

        # Validate both requested values before moving either axis.
        pan_value = None if pan is None else self._validated_pan(pan)

        tilt_value = None if tilt is None else self._validated_tilt(tilt)

        if pan_value is not None:
            self._move_pan(
                pan_value,
                smooth=smooth,
            )

        if tilt_value is not None:
            self._move_tilt(
                tilt_value,
                smooth=smooth,
            )

    def pan(
        self,
        angle: float,
        *,
        smooth: bool = True,
    ) -> None:
        self._require_open()

        self._move_pan(
            self._validated_pan(angle),
            smooth=smooth,
        )

    def tilt(
        self,
        angle: float,
        *,
        smooth: bool = True,
    ) -> None:
        self._require_open()

        self._move_tilt(
            self._validated_tilt(angle),
            smooth=smooth,
        )

    def _validated_pan(
        self,
        angle: object,
    ) -> float:
        value = self._require_finite_number(
            angle,
            name="pan",
        )

        return self._clamp(
            value,
            self._pan_min,
            self._pan_max,
        )

    def _validated_tilt(
        self,
        angle: object,
    ) -> float:
        value = self._require_finite_number(
            angle,
            name="tilt",
        )

        return self._clamp(
            value,
            self._tilt_min,
            self._tilt_max,
        )

    def _move_pan(
        self,
        requested: float,
        *,
        smooth: bool,
    ) -> None:
        servo_angle = self._logical_to_servo_angle(
            requested,
            reversed=self.config.pan_reversed,
        )

        try:
            self.pan_servo.move_to(
                servo_angle,
                smooth=smooth,
            )
        except (
            HardwareError,
            OSError,
            RuntimeError,
        ) as exc:
            raise CameraMountError(f"camera pan failed: {exc}") from exc

        effective_servo_angle = self.pan_servo.get_angle()

        if effective_servo_angle is None:
            raise CameraMountError("camera pan servo did not report its position")

        self._pan = self._servo_to_logical_angle(
            effective_servo_angle,
            reversed=self.config.pan_reversed,
        )

    def _move_tilt(
        self,
        requested: float,
        *,
        smooth: bool,
    ) -> None:
        servo_angle = self._logical_to_servo_angle(
            requested,
            reversed=self.config.tilt_reversed,
        )

        try:
            self.tilt_servo.move_to(
                servo_angle,
                smooth=smooth,
            )
        except (
            HardwareError,
            OSError,
            RuntimeError,
        ) as exc:
            raise CameraMountError(f"camera tilt failed: {exc}") from exc

        effective_servo_angle = self.tilt_servo.get_angle()

        if effective_servo_angle is None:
            raise CameraMountError("camera tilt servo did not report its position")

        self._tilt = self._servo_to_logical_angle(
            effective_servo_angle,
            reversed=self.config.tilt_reversed,
        )

    def center(
        self,
        *,
        smooth: bool = True,
    ) -> None:
        self.look(
            pan=self._pan_center,
            tilt=self._tilt_center,
            smooth=smooth,
        )

    def status(self) -> CameraMountStatus:
        self._require_open()

        return CameraMountStatus(
            pan=self._pan,
            tilt=self._tilt,
            pan_offset=self.pan_offset,
            tilt_offset=self.tilt_offset,
            pan_min=self._pan_min,
            pan_max=self._pan_max,
            tilt_min=self._tilt_min,
            tilt_max=self._tilt_max,
        )

    def _close_constructed_servos(
        self,
    ) -> None:
        for servo in (
            self._tilt_servo,
            self._pan_servo,
        ):
            if servo is None:
                continue

            try:
                servo.close()
            except (
                HardwareError,
                OSError,
                RuntimeError,
            ):
                pass

        self._tilt_servo = None
        self._pan_servo = None

    def close(self) -> None:
        if self._closed:
            return

        first_error: HardwareError | OSError | RuntimeError | None = None

        try:
            for servo in (
                self._tilt_servo,
                self._pan_servo,
            ):
                if servo is None:
                    continue

                try:
                    servo.close()
                except (
                    HardwareError,
                    OSError,
                    RuntimeError,
                ) as exc:
                    if first_error is None:
                        first_error = exc

        finally:
            self._tilt_servo = None
            self._pan_servo = None
            self._pan = None
            self._tilt = None
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

    def _require_open(self) -> None:
        if self._closed:
            raise CameraMountError("camera mount is closed")

    @staticmethod
    def _clamp(
        value: float,
        minimum: float,
        maximum: float,
    ) -> float:
        return max(
            minimum,
            min(
                maximum,
                value,
            ),
        )
