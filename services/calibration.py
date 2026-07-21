from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping, Sequence

from betabox_robotics.calibration import (
    CalibrationManager,
    CameraMountCalibration,
    GrayscaleCalibration,
    MotorCalibration,
    RobotCalibration,
    SteeringCalibration,
)


@dataclass(frozen=True)
class CalibrationStatus:
    saved: bool
    calibration: RobotCalibration

    def to_dict(
        self,
    ) -> dict[str, object]:
        calibration = (
            self.calibration.to_dict()
        )

        grayscale = calibration[
            "grayscale"
        ]

        if isinstance(
            grayscale,
            dict,
        ):
            grayscale["calibrated"] = (
                self.calibration
                .grayscale
                .calibrated
            )

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
            raise TypeError(
                "manager must be a "
                "CalibrationManager"
            )

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
        self._manager.save(
            calibration
        )

        return self.status()

    def save_dict(
        self,
        value: Mapping[str, object],
    ) -> CalibrationStatus:
        """
        Validate and save a complete calibration
        document supplied by an external interface.
        """

        calibration = (
            RobotCalibration.from_dict(
                value
            )
        )

        return self.save(
            calibration
        )

    def update_steering(
        self,
        offset: float,
    ) -> CalibrationStatus:
        current = self.load()

        updated = replace(
            current,
            steering=SteeringCalibration(
                offset=offset
            ),
        )

        return self.save(
            updated
        )

    def update_camera_mount(
        self,
        *,
        pan_offset: float,
        tilt_offset: float,
    ) -> CalibrationStatus:
        current = self.load()

        updated = replace(
            current,
            camera_mount=(
                CameraMountCalibration(
                    pan_offset=pan_offset,
                    tilt_offset=tilt_offset,
                )
            ),
        )

        return self.save(
            updated
        )

    def update_motors(
        self,
        *,
        left_trim: float,
        right_trim: float,
    ) -> CalibrationStatus:
        current = self.load()

        updated = replace(
            current,
            motors=MotorCalibration(
                left_trim=left_trim,
                right_trim=right_trim,
            ),
        )

        return self.save(
            updated
        )

    def update_grayscale(
        self,
        *,
        floor: Sequence[float],
        line: Sequence[float],
    ) -> CalibrationStatus:
        current = self.load()

        updated = replace(
            current,
            grayscale=GrayscaleCalibration(
                floor=self._three_values(
                    floor,
                    name="floor",
                ),
                line=self._three_values(
                    line,
                    name="line",
                ),
            ),
        )

        return self.save(
            updated
        )

    def clear_grayscale(
        self,
    ) -> CalibrationStatus:
        current = self.load()

        updated = replace(
            current,
            grayscale=(
                GrayscaleCalibration()
            ),
        )

        return self.save(
            updated
        )

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
        if len(values) != 3:
            raise ValueError(
                f"{name} must contain "
                "exactly 3 values"
            )

        return (
            float(values[0]),
            float(values[1]),
            float(values[2]),
        )
