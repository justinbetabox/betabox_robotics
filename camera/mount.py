from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from betabox_robotics.hardware import Servo
from betabox_robotics.robots.config import (
    CameraMountConfig,
)

from .exceptions import CameraMountError


@dataclass(frozen=True)
class CameraMountStatus:
    pan: float
    tilt: float

    pan_min: float
    pan_max: float

    tilt_min: float
    tilt_max: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CameraMount:
    """
    Reusable two-axis camera mount.

    Public pan and tilt values are expressed in degrees. The mount owns
    both underlying Servo instances.
    """

    def __init__(
        self,
        config: CameraMountConfig,
    ) -> None:
        self.config = config

        self._pan_servo = Servo(
            config.pan_servo,
            min_angle=config.pan_min_angle,
            max_angle=config.pan_max_angle,
        )

        try:
            self._tilt_servo = Servo(
                config.tilt_servo,
                min_angle=config.tilt_min_angle,
                max_angle=config.tilt_max_angle,
            )
        except Exception:
            self._pan_servo.close()
            raise

        self._pan = float(
            config.pan_center
        )

        self._tilt = float(
            config.tilt_center
        )

        self._closed = False

    @classmethod
    def default(
        cls,
        config: CameraMountConfig,
    ) -> "CameraMount":
        return cls(config)

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def pan_angle(self) -> float:
        return self._pan

    @property
    def tilt_angle(self) -> float:
        return self._tilt

    def look(
        self,
        *,
        pan: float | None = None,
        tilt: float | None = None,
        smooth: bool = True,
    ) -> None:
        self._require_open()

        if pan is not None:
            self.pan(
                pan,
                smooth=smooth,
            )

        if tilt is not None:
            self.tilt(
                tilt,
                smooth=smooth,
            )

    def pan(
        self,
        angle: float,
        *,
        smooth: bool = True,
    ) -> None:
        self._require_open()

        requested = self._clamp(
            float(angle),
            self.config.pan_min_angle,
            self.config.pan_max_angle,
        )

        servo_angle = (
            -requested
            if self.config.pan_reversed
            else requested
        )

        try:
            self._pan_servo.move_to(
                servo_angle,
                smooth=smooth,
            )
        except Exception as exc:
            raise CameraMountError(
                f"camera pan failed: {exc}"
            ) from exc

        self._pan = requested

    def tilt(
        self,
        angle: float,
        *,
        smooth: bool = True,
    ) -> None:
        self._require_open()

        requested = self._clamp(
            float(angle),
            self.config.tilt_min_angle,
            self.config.tilt_max_angle,
        )

        servo_angle = (
            -requested
            if self.config.tilt_reversed
            else requested
        )

        try:
            self._tilt_servo.move_to(
                servo_angle,
                smooth=smooth,
            )
        except Exception as exc:
            raise CameraMountError(
                f"camera tilt failed: {exc}"
            ) from exc

        self._tilt = requested

    def center(
        self,
        *,
        smooth: bool = True,
    ) -> None:
        self.look(
            pan=self.config.pan_center,
            tilt=self.config.tilt_center,
            smooth=smooth,
        )

    def status(self) -> CameraMountStatus:
        self._require_open()

        return CameraMountStatus(
            pan=self._pan,
            tilt=self._tilt,
            pan_min=self.config.pan_min_angle,
            pan_max=self.config.pan_max_angle,
            tilt_min=self.config.tilt_min_angle,
            tilt_max=self.config.tilt_max_angle,
        )

    def close(self) -> None:
        if self._closed:
            return

        self._closed = True

        for servo in (
            self._pan_servo,
            self._tilt_servo,
        ):
            try:
                servo.close()
            except Exception:
                pass

    def deinit(self) -> None:
        self.close()

    def __enter__(self) -> "CameraMount":
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()

    def _require_open(self) -> None:
        if self._closed:
            raise CameraMountError(
                "camera mount is closed"
            )

    @staticmethod
    def _clamp(
        value: float,
        minimum: float,
        maximum: float,
    ) -> float:
        return max(
            minimum,
            min(maximum, value),
        )
