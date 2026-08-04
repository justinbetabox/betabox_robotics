from __future__ import annotations

import threading
import unittest
from types import SimpleNamespace
from unittest.mock import (
    MagicMock,
    call,
    patch,
)

from gpiozero.exc import GPIOPinInUse

from betabox_robotics.calibration.hardware import (
    CalibrationHardware,
    _validate_number,
    _validate_samples,
    _validate_trim,
)
from betabox_robotics.exceptions import (
    RobotBusyError,
)


def make_hardware() -> CalibrationHardware:
    drive_config = SimpleNamespace(
        steering=SimpleNamespace(
            min_angle=-30.0,
            max_angle=30.0,
        )
    )
    camera_mount_config = SimpleNamespace(
        pan_min_angle=-45.0,
        pan_max_angle=45.0,
        tilt_min_angle=-30.0,
        tilt_max_angle=45.0,
    )
    grayscale_config = object()

    return CalibrationHardware(
        drive_config=drive_config,  # type: ignore[arg-type]
        camera_mount_config=(  # type: ignore[arg-type]
            camera_mount_config
        ),
        grayscale_config=(  # type: ignore[arg-type]
            grayscale_config
        ),
    )


class ValidateNumberTests(unittest.TestCase):
    def test_accepts_integer(self) -> None:
        self.assertEqual(
            _validate_number(
                5,
                name="value",
            ),
            5.0,
        )

    def test_accepts_float(self) -> None:
        self.assertEqual(
            _validate_number(
                5.5,
                name="value",
            ),
            5.5,
        )

    def test_rejects_boolean(self) -> None:
        for value in (
            True,
            False,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "value must be a number",
                ),
            ):
                _validate_number(
                    value,
                    name="value",
                )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            "5",
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "value must be a number",
                ),
            ):
                _validate_number(
                    value,
                    name="value",
                )

    def test_rejects_non_finite_values(
        self,
    ) -> None:
        for value in (
            float("nan"),
            float("inf"),
            float("-inf"),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "value must be finite",
                ),
            ):
                _validate_number(
                    value,
                    name="value",
                )


class ValidateTrimTests(unittest.TestCase):
    def test_accepts_valid_trim(self) -> None:
        self.assertEqual(
            _validate_trim(
                0.75,
                name="trim",
            ),
            0.75,
        )

    def test_accepts_boundaries(self) -> None:
        for value in (
            0,
            1,
        ):
            with self.subTest(value=value):
                self.assertEqual(
                    _validate_trim(
                        value,
                        name="trim",
                    ),
                    float(value),
                )

    def test_rejects_out_of_range_trim(
        self,
    ) -> None:
        for value in (
            -0.1,
            1.1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "trim must be between 0 and 1",
                ),
            ):
                _validate_trim(
                    value,
                    name="trim",
                )

    def test_rejects_invalid_type(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "trim must be a number",
        ):
            _validate_trim(
                "0.5",
                name="trim",
            )


class ValidateSamplesTests(unittest.TestCase):
    def test_accepts_positive_integer(self) -> None:
        self.assertEqual(
            _validate_samples(10),
            10,
        )

    def test_accepts_one(self) -> None:
        self.assertEqual(
            _validate_samples(1),
            1,
        )

    def test_rejects_boolean(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "samples must be an integer",
        ):
            _validate_samples(True)

    def test_rejects_non_integer(self) -> None:
        for value in (
            1.0,
            "10",
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "samples must be an integer",
                ),
            ):
                _validate_samples(value)

    def test_rejects_non_positive_integer(
        self,
    ) -> None:
        for value in (
            0,
            -1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "samples must be at least 1",
                ),
            ):
                _validate_samples(value)


class CalibrationHardwareValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hardware = make_hardware()

    def test_preview_steering_accepts_boundaries(
        self,
    ) -> None:
        with patch.object(
            self.hardware,
            "_run",
        ) as run:
            for offset in (
                -30,
                30,
            ):
                with self.subTest(offset=offset):
                    self.hardware.preview_steering(offset=offset)

        self.assertEqual(
            run.call_args_list,
            [
                call(
                    self.hardware._preview_steering,
                    owner=("Launchpad Steering Calibration"),
                    offset=-30.0,
                ),
                call(
                    self.hardware._preview_steering,
                    owner=("Launchpad Steering Calibration"),
                    offset=30.0,
                ),
            ],
        )

    def test_preview_steering_rejects_out_of_range(
        self,
    ) -> None:
        for offset in (
            -30.1,
            30.1,
        ):
            with (
                self.subTest(offset=offset),
                self.assertRaisesRegex(
                    ValueError,
                    "steering offset must be between",
                ),
                patch.object(
                    self.hardware,
                    "_run",
                ) as run,
            ):
                self.hardware.preview_steering(offset=offset)

            run.assert_not_called()

    def test_preview_steering_rejects_invalid_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "steering offset must be a number",
        ):
            self.hardware.preview_steering(
                offset="0"  # type: ignore[arg-type]
            )

    def test_preview_camera_mount_forwards_values(
        self,
    ) -> None:
        with patch.object(
            self.hardware,
            "_run",
        ) as run:
            self.hardware.preview_camera_mount(
                pan_offset=10,
                tilt_offset=-5,
            )

        run.assert_called_once_with(
            self.hardware._preview_camera_mount,
            owner=("Launchpad Camera Calibration"),
            pan_offset=10.0,
            tilt_offset=-5.0,
        )

    def test_preview_camera_mount_accepts_boundaries(
        self,
    ) -> None:
        with patch.object(
            self.hardware,
            "_run",
        ) as run:
            self.hardware.preview_camera_mount(
                pan_offset=-45,
                tilt_offset=45,
            )

        run.assert_called_once()

    def test_preview_camera_mount_rejects_pan_out_of_range(
        self,
    ) -> None:
        for value in (
            -45.1,
            45.1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "pan offset must be between",
                ),
            ):
                self.hardware.preview_camera_mount(
                    pan_offset=value,
                    tilt_offset=0,
                )

    def test_preview_camera_mount_rejects_tilt_out_of_range(
        self,
    ) -> None:
        for value in (
            -30.1,
            45.1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "tilt offset must be between",
                ),
            ):
                self.hardware.preview_camera_mount(
                    pan_offset=0,
                    tilt_offset=value,
                )

    def test_preview_motor_trim_forwards_values(
        self,
    ) -> None:
        with patch.object(
            self.hardware,
            "_run",
        ) as run:
            self.hardware.preview_motor_trim(
                left_trim=0.8,
                right_trim=0.9,
                steering_offset=5,
            )

        run.assert_called_once_with(
            self.hardware._preview_motor_trim,
            owner=("Launchpad Motor Calibration"),
            left_trim=0.8,
            right_trim=0.9,
            steering_offset=5.0,
        )

    def test_preview_motor_trim_rejects_invalid_trims(
        self,
    ) -> None:
        cases = (
            (
                -0.1,
                1.0,
                "left trim",
            ),
            (
                1.1,
                1.0,
                "left trim",
            ),
            (
                1.0,
                -0.1,
                "right trim",
            ),
            (
                1.0,
                1.1,
                "right trim",
            ),
        )

        for left, right, message in cases:
            with (
                self.subTest(
                    left=left,
                    right=right,
                ),
                self.assertRaisesRegex(
                    ValueError,
                    message,
                ),
            ):
                self.hardware.preview_motor_trim(
                    left_trim=left,
                    right_trim=right,
                    steering_offset=0,
                )

    def test_preview_motor_trim_rejects_steering_out_of_range(
        self,
    ) -> None:
        for value in (
            -30.1,
            30.1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "steering offset must be between",
                ),
            ):
                self.hardware.preview_motor_trim(
                    left_trim=1.0,
                    right_trim=1.0,
                    steering_offset=value,
                )

    def test_sample_grayscale_forwards_samples(
        self,
    ) -> None:
        expected = [
            100,
            200,
            300,
        ]

        with patch.object(
            self.hardware,
            "_run",
            return_value=expected,
        ) as run:
            result = self.hardware.sample_grayscale(samples=5)

        self.assertIs(
            result,
            expected,
        )
        run.assert_called_once_with(
            self.hardware._sample_grayscale,
            owner=("Launchpad Grayscale Calibration"),
            samples=5,
        )

    def test_sample_grayscale_rejects_invalid_samples(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            self.hardware.sample_grayscale(samples=0)


class CalibrationHardwareRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hardware = make_hardware()

    def test_run_acquires_executes_cleans_and_releases(
        self,
    ) -> None:
        ownership = MagicMock()
        operation = MagicMock(return_value="result")

        with (
            patch(
                "betabox_robotics.calibration.hardware.RobotOwnership",
                return_value=ownership,
            ) as ownership_type,
            patch(
                "betabox_robotics.calibration.hardware.close_gpio_factory"
            ) as close_factory,
        ):
            result = self.hardware._run(
                operation,
                owner="Test Owner",
                value=5,
            )

        self.assertEqual(
            result,
            "result",
        )
        ownership_type.assert_called_once_with(owner="Test Owner")
        ownership.acquire.assert_called_once_with()
        operation.assert_called_once_with(value=5)
        close_factory.assert_called_once_with()
        ownership.release.assert_called_once_with()

    def test_run_cleans_up_when_operation_fails(
        self,
    ) -> None:
        ownership = MagicMock()
        operation_error = RuntimeError("operation failed")

        with (
            patch(
                "betabox_robotics.calibration.hardware.RobotOwnership",
                return_value=ownership,
            ),
            patch(
                "betabox_robotics.calibration.hardware.close_gpio_factory"
            ) as close_factory,
            self.assertRaises(RuntimeError) as context,
        ):
            self.hardware._run(
                MagicMock(side_effect=operation_error),
                owner="Test Owner",
            )

        self.assertIs(
            context.exception,
            operation_error,
        )
        close_factory.assert_called_once_with()
        ownership.release.assert_called_once_with()

    def test_run_wraps_gpio_pin_in_use(
        self,
    ) -> None:
        ownership = MagicMock()
        error = GPIOPinInUse(4, "test")

        with (
            patch(
                "betabox_robotics.calibration.hardware.RobotOwnership",
                return_value=ownership,
            ),
            patch(
                "betabox_robotics.calibration.hardware.close_gpio_factory"
            ) as close_factory,
            self.assertRaisesRegex(
                RobotBusyError,
                "could not be acquired",
            ) as context,
        ):
            self.hardware._run(
                MagicMock(side_effect=error),
                owner="Test Owner",
            )

        self.assertIs(
            context.exception.__cause__,
            error,
        )
        close_factory.assert_called_once_with()
        ownership.release.assert_called_once_with()

    def test_failed_ownership_acquisition_does_not_cleanup(
        self,
    ) -> None:
        ownership = MagicMock()
        ownership.acquire.side_effect = RobotBusyError("already owned")
        operation = MagicMock()

        with (
            patch(
                "betabox_robotics.calibration.hardware.RobotOwnership",
                return_value=ownership,
            ),
            patch(
                "betabox_robotics.calibration.hardware.close_gpio_factory"
            ) as close_factory,
            self.assertRaisesRegex(
                RobotBusyError,
                "already owned",
            ),
        ):
            self.hardware._run(
                operation,
                owner="Test Owner",
            )

        operation.assert_not_called()
        close_factory.assert_not_called()
        ownership.release.assert_not_called()

    def test_release_runs_when_gpio_cleanup_fails(
        self,
    ) -> None:
        ownership = MagicMock()
        cleanup_error = RuntimeError("cleanup failed")

        with (
            patch(
                "betabox_robotics.calibration.hardware.RobotOwnership",
                return_value=ownership,
            ),
            patch(
                "betabox_robotics.calibration.hardware.close_gpio_factory",
                side_effect=cleanup_error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            self.hardware._run(
                MagicMock(),
                owner="Test Owner",
            )

        self.assertIs(
            context.exception,
            cleanup_error,
        )
        ownership.release.assert_called_once_with()

    def test_run_serializes_operations(
        self,
    ) -> None:
        self.assertIsInstance(
            self.hardware._operation_lock,
            type(threading.Lock()),
        )


class CalibrationHardwareOperationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hardware = make_hardware()

    def test_preview_steering_uses_injected_drive_config(
        self,
    ) -> None:
        drive = MagicMock()
        context = MagicMock()
        context.__enter__.return_value = drive
        context.__exit__.return_value = False

        with patch(
            "betabox_robotics.calibration.hardware.Drive.default",
            return_value=context,
        ) as default:
            self.hardware._preview_steering(offset=5.0)

        default.assert_called_once_with(
            self.hardware._drive_config,
            steering_offset=5.0,
        )
        drive.center.assert_called_once_with()

    def test_preview_camera_mount_uses_injected_config(
        self,
    ) -> None:
        camera = MagicMock()
        context = MagicMock()
        context.__enter__.return_value = camera
        context.__exit__.return_value = False

        with patch(
            "betabox_robotics.calibration.hardware.CameraMount.default",
            return_value=context,
        ) as default:
            self.hardware._preview_camera_mount(
                pan_offset=5.0,
                tilt_offset=-2.0,
            )

        default.assert_called_once_with(
            self.hardware._camera_mount_config,
            pan_offset=5.0,
            tilt_offset=-2.0,
        )
        camera.center.assert_called_once_with()

    def test_preview_motor_trim_runs_and_stops_drive(
        self,
    ) -> None:
        drive = MagicMock()
        context = MagicMock()
        context.__enter__.return_value = drive
        context.__exit__.return_value = False

        with (
            patch(
                "betabox_robotics.calibration.hardware.Drive.default",
                return_value=context,
            ) as default,
            patch("betabox_robotics.calibration.hardware.sleep") as sleep,
        ):
            self.hardware._preview_motor_trim(
                left_trim=0.8,
                right_trim=0.9,
                steering_offset=4.0,
            )

        default.assert_called_once_with(
            self.hardware._drive_config,
            left_trim=0.8,
            right_trim=0.9,
            steering_offset=4.0,
        )
        drive.center.assert_called_once_with()
        drive.forward.assert_called_once_with(25)
        sleep.assert_called_once_with(1.5)
        drive.stop.assert_called_once_with()

    def test_preview_motor_trim_stops_after_forward_failure(
        self,
    ) -> None:
        drive = MagicMock()
        drive.forward.side_effect = RuntimeError("motor failure")

        context = MagicMock()
        context.__enter__.return_value = drive
        context.__exit__.return_value = False

        with (
            patch(
                "betabox_robotics.calibration.hardware.Drive.default",
                return_value=context,
            ),
            self.assertRaisesRegex(
                RuntimeError,
                "motor failure",
            ),
        ):
            self.hardware._preview_motor_trim(
                left_trim=0.8,
                right_trim=0.9,
                steering_offset=4.0,
            )

        drive.stop.assert_called_once_with()

    def test_sample_grayscale_averages_readings(
        self,
    ) -> None:
        grayscale = MagicMock()
        grayscale.read.side_effect = [
            (
                100,
                200,
                300,
            ),
            (
                110,
                220,
                330,
            ),
            (
                120,
                240,
                360,
            ),
        ]

        context = MagicMock()
        context.__enter__.return_value = grayscale
        context.__exit__.return_value = False

        with patch(
            "betabox_robotics.calibration.hardware.Grayscale.default",
            return_value=context,
        ) as default:
            result = self.hardware._sample_grayscale(samples=3)

        default.assert_called_once_with(self.hardware._grayscale_config)
        self.assertEqual(
            grayscale.read.call_count,
            3,
        )
        self.assertEqual(
            result,
            [
                110,
                220,
                330,
            ],
        )

    def test_sample_grayscale_rounds_averages(
        self,
    ) -> None:
        grayscale = MagicMock()
        grayscale.read.side_effect = [
            (
                100,
                100,
                100,
            ),
            (
                101,
                102,
                103,
            ),
        ]

        context = MagicMock()
        context.__enter__.return_value = grayscale
        context.__exit__.return_value = False

        with patch(
            "betabox_robotics.calibration.hardware.Grayscale.default",
            return_value=context,
        ):
            result = self.hardware._sample_grayscale(samples=2)

        self.assertEqual(
            result,
            [
                100,
                101,
                102,
            ],
        )


if __name__ == "__main__":
    unittest.main()
