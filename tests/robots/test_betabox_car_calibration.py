from __future__ import annotations

import unittest

from unittest.mock import MagicMock, patch

from betabox_robotics.calibration import (
    GrayscaleCalibration,
    MotorCalibration,
    RobotCalibration,
    SteeringCalibration,
)
from betabox_robotics.robots.betabox_car import (
    BetaboxCar,
)


class BetaboxCarCalibrationTests(
    unittest.TestCase
):
    @patch(
        "betabox_robotics.robots.betabox_car."
        "RobotOwnership"
    )
    @patch(
        "betabox_robotics.robots.betabox_car."
        "System"
    )
    @patch(
        "betabox_robotics.robots.betabox_car."
        "Audio"
    )
    @patch(
        "betabox_robotics.robots.betabox_car."
        "VisionClient"
    )
    @patch(
        "betabox_robotics.robots.betabox_car."
        "CameraMount"
    )
    @patch(
        "betabox_robotics.robots.betabox_car."
        "Sensors"
    )
    @patch(
        "betabox_robotics.robots.betabox_car."
        "Drive"
    )
    def test_applies_calibration(
        self,
        drive_class: MagicMock,
        sensors_class: MagicMock,
        camera_mount_class: MagicMock,
        vision_class: MagicMock,
        audio_class: MagicMock,
        system_class: MagicMock,
        ownership_class: MagicMock,
    ) -> None:
        drive = MagicMock()
        sensors = MagicMock()

        drive_class.default.return_value = drive
        sensors_class.default.return_value = sensors

        camera_mount_class.default.return_value = (
            MagicMock()
        )
        vision_class.default.return_value = (
            MagicMock()
        )
        audio_class.default.return_value = (
            MagicMock()
        )
        system_class.default.return_value = (
            MagicMock()
        )

        ownership = MagicMock()
        ownership_class.return_value = ownership

        calibration = RobotCalibration(
            steering=SteeringCalibration(
                offset=2.5,
            ),
            motors=MotorCalibration(
                left_trim=0.95,
                right_trim=1.0,
            ),
            grayscale=GrayscaleCalibration(
                floor=(
                    900,
                    910,
                    920,
                ),
                line=(
                    250,
                    260,
                    270,
                ),
            ),
        )

        robot = BetaboxCar(
            calibration=calibration
        )

        drive_class.default.assert_called_once()

        drive_kwargs = (
            drive_class
            .default
            .call_args
            .kwargs
        )

        self.assertEqual(
            drive_kwargs["left_trim"],
            0.95,
        )
        self.assertEqual(
            drive_kwargs["right_trim"],
            1.0,
        )
        self.assertEqual(
            drive_kwargs["steering_offset"],
            2.5,
        )

        (
            sensors
            .grayscale
            .set_calibration
            .assert_called_once_with(
                (
                    900.0,
                    910.0,
                    920.0,
                ),
                (
                    250.0,
                    260.0,
                    270.0,
                ),
            )
        )

        robot.close()


if __name__ == "__main__":
    unittest.main()
