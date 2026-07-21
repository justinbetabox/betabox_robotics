from __future__ import annotations

import tempfile
import unittest

from pathlib import Path

from betabox_robotics.calibration import (
    CalibrationManager,
)
from betabox_robotics.services.calibration import (
    CalibrationService,
)


class CalibrationServiceTests(
    unittest.TestCase
):
    def setUp(
        self,
    ) -> None:
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )

        path = (
            Path(
                self.temporary_directory.name
            )
            / "calibration.json"
        )

        self.manager = CalibrationManager(
            path
        )

        self.service = CalibrationService(
            self.manager
        )

    def tearDown(
        self,
    ) -> None:
        self.temporary_directory.cleanup()

    def test_initial_status_uses_defaults(
        self,
    ) -> None:
        status = self.service.status()

        self.assertFalse(
            status.saved
        )

        self.assertEqual(
            status.calibration
            .steering
            .offset,
            0.0,
        )

        payload = status.to_dict()

        grayscale = (
            payload["calibration"][
                "grayscale"
            ]
        )

        self.assertFalse(
            grayscale["calibrated"]
        )

    def test_update_steering_preserves_other_sections(
        self,
    ) -> None:
        status = (
            self.service
            .update_steering(
                2.5
            )
        )

        self.assertTrue(
            status.saved
        )

        self.assertEqual(
            status.calibration
            .steering
            .offset,
            2.5,
        )

        self.assertEqual(
            status.calibration
            .motors
            .left_trim,
            1.0,
        )

    def test_update_motors(
        self,
    ) -> None:
        status = (
            self.service
            .update_motors(
                left_trim=0.95,
                right_trim=1.0,
            )
        )

        self.assertEqual(
            status.calibration
            .motors
            .left_trim,
            0.95,
        )

        self.assertEqual(
            status.calibration
            .motors
            .right_trim,
            1.0,
        )

    def test_update_grayscale(
        self,
    ) -> None:
        status = (
            self.service
            .update_grayscale(
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
            )
        )

        self.assertTrue(
            status.calibration
            .grayscale
            .calibrated
        )

        self.assertEqual(
            status.calibration
            .grayscale
            .floor,
            (
                900.0,
                910.0,
                920.0,
            ),
        )

    def test_clear_grayscale(
        self,
    ) -> None:
        self.service.update_grayscale(
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
        )

        status = (
            self.service
            .clear_grayscale()
        )

        self.assertFalse(
            status.calibration
            .grayscale
            .calibrated
        )

    def test_reset_removes_saved_file(
        self,
    ) -> None:
        self.service.update_steering(
            2.0
        )

        status = self.service.reset()

        self.assertFalse(
            status.saved
        )

        self.assertEqual(
            status.calibration
            .steering
            .offset,
            0.0,
        )

    def test_invalid_steering_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ValueError
        ):
            self.service.update_steering(
                31.0
            )

        self.assertFalse(
            self.manager.exists()
        )

    def test_invalid_motor_trim_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ValueError
        ):
            self.service.update_motors(
                left_trim=1.1,
                right_trim=1.0,
            )

    def test_grayscale_requires_three_values(
        self,
    ) -> None:
        with self.assertRaises(
            ValueError
        ):
            self.service.update_grayscale(
                floor=(900, 910),
                line=(
                    250,
                    260,
                    270,
                ),
            )

    def test_update_camera_mount(
        self,
    ) -> None:
        status = (
            self.service
            .update_camera_mount(
                pan_offset=3.0,
                tilt_offset=-2.0,
            )
        )

        self.assertEqual(
            status.calibration
            .camera_mount
            .pan_offset,
            3.0,
        )

        self.assertEqual(
            status.calibration
            .camera_mount
            .tilt_offset,
            -2.0,
        )


if __name__ == "__main__":
    unittest.main()
