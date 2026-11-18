from __future__ import annotations

import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from betabox_robotics.calibration import (
    CalibrationManager,
    RobotCalibration,
)
from betabox_robotics.runtime.runtime import RobotRuntime


class RuntimeCalibrationTests(unittest.TestCase):
    def test_hardware_uses_saved_calibration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = CalibrationManager(Path(directory) / "calibration.json")

            manager.save(
                RobotCalibration.from_dict(
                    {
                        "version": 1,
                        "steering": {"offset": 21.0},
                        "camera_mount": {
                            "pan_offset": -20.0,
                            "tilt_offset": 17.0,
                        },
                        "motors": {
                            "left_trim": 0.8,
                            "right_trim": 0.9,
                        },
                        "grayscale": {
                            "floor": None,
                            "line": None,
                        },
                    }
                )
            )

            hardware_classes = (
                "I2C",
                "ADC",
                "Battery",
                "Grayscale",
                "Ultrasonic",
                "PWM",
                "Motor",
                "Pin",
                "Servo",
                "Drive",
                "CameraMount",
            )

            with ExitStack() as stack:
                mocks = {
                    name: stack.enter_context(
                        patch(f"betabox_robotics.runtime.runtime.{name}")
                    )
                    for name in hardware_classes
                }

                runtime = RobotRuntime(calibration_manager=manager)

                runtime._initialize_hardware()

                self.assertEqual(
                    mocks["Servo"].call_args.kwargs["offset"],
                    21.0,
                )

                drive_kwargs = mocks["Drive"].call_args.kwargs

                self.assertEqual(drive_kwargs["left_trim"], 0.8)
                self.assertEqual(drive_kwargs["right_trim"], 0.9)

                camera_kwargs = mocks["CameraMount"].default.call_args.kwargs

                self.assertEqual(
                    camera_kwargs["pan_offset"],
                    -20.0,
                )
                self.assertEqual(
                    camera_kwargs["tilt_offset"],
                    17.0,
                )
