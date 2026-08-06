from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from betabox_robotics.calibration import (
    CalibrationManager,
    CameraMountCalibration,
    GrayscaleCalibration,
    MotorCalibration,
    RobotCalibration,
    SteeringCalibration,
)


def _validate_float(
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


def _validate_mapping(
    value: object,
    *,
    name: str,
) -> Mapping[str, object]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError(f"{name} must be a mapping")

    return value


@dataclass(frozen=True, slots=True)
class CalibrationStatus:
    saved: bool
    calibration: RobotCalibration

    def __post_init__(self) -> None:
        if not isinstance(
            self.saved,
            bool,
        ):
            raise TypeError("saved must be a boolean")

        if not isinstance(
            self.calibration,
            RobotCalibration,
        ):
            raise TypeError("calibration must be a RobotCalibration")

    def to_dict(
        self,
    ) -> dict[str, object]:
        calibration = self.calibration.to_dict()

        grayscale = calibration.get("grayscale")

        if isinstance(
            grayscale,
            dict,
        ):
            grayscale["calibrated"] = self.calibration.grayscale.calibrated

        return {
            "saved": self.saved,
            "calibration": calibration,
        }


class CalibrationService:
    """
    Application-level calibration operations.

    The service owns calibration updates and delegates
    persistence to CalibrationManager. Callers do not
    need to construct replacement RobotCalibration
    objects manually.
    """

    def __init__(
        self,
        manager: CalibrationManager,
    ) -> None:
        if not isinstance(
            manager,
            CalibrationManager,
        ):
            raise TypeError("manager must be a CalibrationManager")

        self._manager = manager

    def status(
        self,
    ) -> CalibrationStatus:
        return CalibrationStatus(
            saved=self._manager.exists(),
            calibration=self._manager.load(),
        )

    def load(
        self,
    ) -> RobotCalibration:
        return self._manager.load()

    def save(
        self,
        calibration: RobotCalibration,
    ) -> CalibrationStatus:
        if not isinstance(
            calibration,
            RobotCalibration,
        ):
            raise TypeError("calibration must be a RobotCalibration")

        self._manager.save(calibration)

        return self.status()

    def save_dict(
        self,
        value: Mapping[str, object],
    ) -> CalibrationStatus:
        """
        Validate and save a complete calibration
        document supplied by an external interface.
        """

        value_mapping = _validate_mapping(
            value,
            name="value",
        )

        calibration = RobotCalibration.from_dict(value_mapping)

        return self.save(calibration)

    def update_steering(
        self,
        offset: float,
    ) -> CalibrationStatus:
        offset_value = _validate_float(
            offset,
            name="offset",
        )
        current = self.load()

        updated = replace(
            current,
            steering=SteeringCalibration(offset=offset_value),
        )

        return self.save(updated)

    def update_camera_mount(
        self,
        *,
        pan_offset: float,
        tilt_offset: float,
    ) -> CalibrationStatus:
        pan_offset_value = _validate_float(
            pan_offset,
            name="pan_offset",
        )
        tilt_offset_value = _validate_float(
            tilt_offset,
            name="tilt_offset",
        )
        current = self.load()

        updated = replace(
            current,
            camera_mount=(
                CameraMountCalibration(
                    pan_offset=pan_offset_value,
                    tilt_offset=tilt_offset_value,
                )
            ),
        )

        return self.save(updated)

    def update_motors(
        self,
        *,
        left_trim: float,
        right_trim: float,
    ) -> CalibrationStatus:
        left_trim_value = _validate_float(
            left_trim,
            name="left_trim",
        )
        right_trim_value = _validate_float(
            right_trim,
            name="right_trim",
        )
        current = self.load()

        updated = replace(
            current,
            motors=MotorCalibration(
                left_trim=left_trim_value,
                right_trim=right_trim_value,
            ),
        )

        return self.save(updated)

    def update_grayscale(
        self,
        *,
        floor: Sequence[float],
        line: Sequence[float],
    ) -> CalibrationStatus:
        floor_values = self._three_values(
            floor,
            name="floor",
        )
        line_values = self._three_values(
            line,
            name="line",
        )
        current = self.load()

        updated = replace(
            current,
            grayscale=GrayscaleCalibration(
                floor=floor_values,
                line=line_values,
            ),
        )

        return self.save(updated)

    def clear_grayscale(
        self,
    ) -> CalibrationStatus:
        current = self.load()

        updated = replace(
            current,
            grayscale=GrayscaleCalibration(),
        )

        return self.save(updated)

    def reset(
        self,
    ) -> CalibrationStatus:
        self._manager.reset()

        return self.status()

    def exists(
        self,
    ) -> bool:
        return self._manager.exists()

    @staticmethod
    def _three_values(
        values: Sequence[float],
        *,
        name: str,
    ) -> tuple[
        float,
        float,
        float,
    ]:
        if isinstance(
            values,
            str | bytes,
        ) or not isinstance(
            values,
            Sequence,
        ):
            raise TypeError(f"{name} must be a sequence")

        if len(values) != 3:
            raise ValueError(f"{name} must contain exactly 3 values")

        return (
            _validate_float(
                values[0],
                name=f"{name}[0]",
            ),
            _validate_float(
                values[1],
                name=f"{name}[1]",
            ),
            _validate_float(
                values[2],
                name=f"{name}[2]",
            ),
        )
