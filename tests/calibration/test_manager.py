from __future__ import annotations

import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from betabox_robotics.calibration import (
    CalibrationManager,
    MotorCalibration,
    RobotCalibration,
    SteeringCalibration,
)


class CalibrationManagerTests(
    unittest.TestCase
):
    def test_load_returns_defaults_when_missing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = (
                Path(directory)
                / "calibration.json"
            )

            manager = CalibrationManager(
                path
            )

            self.assertFalse(
                manager.exists()
            )

            self.assertEqual(
                manager.load(),
                RobotCalibration.default(),
            )

    def test_save_load_and_exists(
        self,
    ) -> None:
        calibration = RobotCalibration(
            steering=SteeringCalibration(
                offset=3.0,
            ),
            motors=MotorCalibration(
                left_trim=0.96,
                right_trim=1.0,
            ),
        )

        with tempfile.TemporaryDirectory() as directory:
            path = (
                Path(directory)
                / "state"
                / "calibration.json"
            )

            manager = CalibrationManager(
                path
            )

            saved = manager.save(
                calibration
            )

            self.assertEqual(
                saved,
                calibration,
            )

            self.assertTrue(
                manager.exists()
            )

            self.assertEqual(
                manager.load(),
                calibration,
            )

    def test_reset(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = (
                Path(directory)
                / "calibration.json"
            )

            manager = CalibrationManager(
                path
            )

            manager.save(
                RobotCalibration.default()
            )

            self.assertTrue(
                manager.reset()
            )

            self.assertFalse(
                manager.exists()
            )

            self.assertFalse(
                manager.reset()
            )

    def test_save_rejects_wrong_type(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = CalibrationManager(
                Path(directory)
                / "calibration.json"
            )

            with self.assertRaises(
                TypeError
            ):
                manager.save(  # type: ignore[arg-type]
                    {}
                )

    @patch(
        "betabox_robotics.robots.betabox_car."
        "BetaboxCar"
    )
    def test_create_car_loads_calibration(
        self,
        robot_class,
    ) -> None:
        calibration = RobotCalibration(
            steering=SteeringCalibration(
                offset=2.0,
            )
        )

        with tempfile.TemporaryDirectory() as directory:
            path = (
                Path(directory)
                / "calibration.json"
            )

            manager = CalibrationManager(
                path
            )

            manager.save(
                calibration
            )

            robot = manager.create_car(
                owner="Calibration test"
            )

            robot_class.assert_called_once_with(
                calibration=calibration,
                owner="Calibration test",
            )

            self.assertEqual(
                robot,
                robot_class.return_value,
            )

    def test_create_car_rejects_calibration_override(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = CalibrationManager(
                Path(directory)
                / "calibration.json"
            )

            with self.assertRaises(
                TypeError
            ):
                manager.create_car(
                    calibration=(
                        RobotCalibration.default()
                    )
                )


if __name__ == "__main__":
    unittest.main()
