from __future__ import annotations

import math
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from betabox_robotics.drive import (
    Drive,
    DriveError,
    DriveStatus,
)
from betabox_robotics.hardware import (
    PWM,
    HardwareError,
    Motor,
    MotorError,
    Pin,
    PinMode,
    Servo,
)
from betabox_robotics.hardware.board import Pins


def make_motor() -> MagicMock:
    motor = MagicMock(spec=Motor)
    motor.closed = False
    motor.get_speed.return_value = 0.0
    return motor


def make_servo() -> MagicMock:
    servo = MagicMock(spec=Servo)
    servo.closed = False
    servo.offset = 0.0
    servo.get_angle.return_value = None
    return servo


def make_drive(
    *,
    left_trim: float = 1.0,
    right_trim: float = 1.0,
) -> tuple[
    Drive,
    MagicMock,
    MagicMock,
    MagicMock,
]:
    left_motor = make_motor()
    right_motor = make_motor()
    steering = make_servo()

    drive = Drive(
        left_motor,
        right_motor,
        steering,
        left_trim=left_trim,
        right_trim=right_trim,
    )

    return (
        drive,
        left_motor,
        right_motor,
        steering,
    )


def make_drive_config() -> SimpleNamespace:
    return SimpleNamespace(
        left_motor=SimpleNamespace(
            pwm=Pins.P12,
            direction=Pins.D4,
            reversed=False,
            trim=0.95,
        ),
        right_motor=SimpleNamespace(
            pwm=Pins.P13,
            direction=Pins.D5,
            reversed=True,
            trim=0.90,
        ),
        steering=SimpleNamespace(
            servo=Pins.P2,
            min_angle=-30.0,
            max_angle=30.0,
        ),
    )


def make_factory_hardware() -> tuple[
    MagicMock,
    MagicMock,
    MagicMock,
    MagicMock,
    MagicMock,
]:
    left_pwm = MagicMock(spec=PWM)
    right_pwm = MagicMock(spec=PWM)
    steering_pwm = MagicMock(spec=PWM)

    for pwm in (
        left_pwm,
        right_pwm,
        steering_pwm,
    ):
        pwm.CLOCK = PWM.CLOCK

    left_pin = MagicMock(spec=Pin)
    right_pin = MagicMock(spec=Pin)

    return (
        left_pwm,
        right_pwm,
        steering_pwm,
        left_pin,
        right_pin,
    )


class DriveStatusTests(unittest.TestCase):
    def test_to_dict_returns_all_fields(
        self,
    ) -> None:
        status = DriveStatus(
            closed=False,
            left_trim=0.95,
            right_trim=0.90,
            steering_offset=4.0,
        )

        self.assertEqual(
            status.to_dict(),
            {
                "closed": False,
                "left_trim": 0.95,
                "right_trim": 0.90,
                "steering_offset": 4.0,
            },
        )


class DriveConstructionTests(unittest.TestCase):
    def test_constructor_stores_components_and_trim(
        self,
    ) -> None:
        drive, left, right, steering = make_drive(
            left_trim=0.95,
            right_trim=0.90,
        )

        self.assertIs(
            drive.left_motor,
            left,
        )
        self.assertIs(
            drive.right_motor,
            right,
        )
        self.assertIs(
            drive.steering,
            steering,
        )

        self.assertEqual(
            drive.left_trim,
            0.95,
        )
        self.assertEqual(
            drive.right_trim,
            0.90,
        )
        self.assertFalse(
            drive.closed,
        )

    def test_constructor_requires_left_motor(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "left_motor must be a Motor instance",
        ):
            Drive(
                object(),  # type: ignore[arg-type]
                make_motor(),
                make_servo(),
            )

    def test_constructor_requires_right_motor(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "right_motor must be a Motor instance",
        ):
            Drive(
                make_motor(),
                object(),  # type: ignore[arg-type]
                make_servo(),
            )

    def test_constructor_requires_steering_servo(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "steering must be a Servo instance",
        ):
            Drive(
                make_motor(),
                make_motor(),
                object(),  # type: ignore[arg-type]
            )

    def test_constructor_rejects_negative_left_trim(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            DriveError,
            "left_trim cannot be negative",
        ):
            Drive(
                make_motor(),
                make_motor(),
                make_servo(),
                left_trim=-0.1,
            )

    def test_constructor_rejects_negative_right_trim(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            DriveError,
            "right_trim cannot be negative",
        ):
            Drive(
                make_motor(),
                make_motor(),
                make_servo(),
                right_trim=-0.1,
            )

    def test_constructor_rejects_boolean_trim(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "left_trim must be a number",
        ):
            Drive(
                make_motor(),
                make_motor(),
                make_servo(),
                left_trim=True,
            )

    def test_constructor_rejects_non_finite_trim(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "right_trim must be finite",
        ):
            Drive(
                make_motor(),
                make_motor(),
                make_servo(),
                right_trim=math.nan,
            )


class DriveFactoryTests(unittest.TestCase):
    def test_default_constructs_configured_hardware(
        self,
    ) -> None:
        config = make_drive_config()

        (
            left_pwm,
            right_pwm,
            steering_pwm,
            left_pin,
            right_pin,
        ) = make_factory_hardware()

        with (
            patch(
                "betabox_robotics.drive.drive.PWM",
                side_effect=[
                    left_pwm,
                    right_pwm,
                ],
            ) as motor_pwm_type,
            patch(
                "betabox_robotics.hardware.servo.PWM",
                return_value=steering_pwm,
            ) as servo_pwm_type,
            patch(
                "betabox_robotics.drive.drive.Pin",
                side_effect=[
                    left_pin,
                    right_pin,
                ],
            ) as pin_type,
        ):
            drive = Drive.default(
                config,
                steering_offset=3.5,
            )

        self.assertEqual(
            motor_pwm_type.call_args_list,
            [
                call(config.left_motor.pwm),
                call(config.right_motor.pwm),
            ],
        )

        servo_pwm_type.assert_called_once_with(
            config.steering.servo,
            address=None,
            bus=None,
        )

        self.assertEqual(
            pin_type.call_args_list,
            [
                call(
                    config.left_motor.direction,
                    mode=PinMode.OUT,
                ),
                call(
                    config.right_motor.direction,
                    mode=PinMode.OUT,
                ),
            ],
        )

        self.assertIsInstance(
            drive.left_motor,
            Motor,
        )
        self.assertIsInstance(
            drive.right_motor,
            Motor,
        )
        self.assertIsInstance(
            drive.steering,
            Servo,
        )

        self.assertIs(
            drive.left_motor.pwm,
            left_pwm,
        )
        self.assertIs(
            drive.left_motor.direction,
            left_pin,
        )
        self.assertFalse(
            drive.left_motor.reversed,
        )

        self.assertIs(
            drive.right_motor.pwm,
            right_pwm,
        )
        self.assertIs(
            drive.right_motor.direction,
            right_pin,
        )
        self.assertTrue(
            drive.right_motor.reversed,
        )

        self.assertEqual(
            drive.steering.min_angle,
            -30.0,
        )
        self.assertEqual(
            drive.steering.max_angle,
            30.0,
        )
        self.assertEqual(
            drive.steering.offset,
            3.5,
        )

        self.assertEqual(
            drive.left_trim,
            0.95,
        )
        self.assertEqual(
            drive.right_trim,
            0.90,
        )

    def test_default_applies_all_overrides(
        self,
    ) -> None:
        config = make_drive_config()

        (
            left_pwm,
            right_pwm,
            steering_pwm,
            left_pin,
            right_pin,
        ) = make_factory_hardware()

        with (
            patch(
                "betabox_robotics.drive.drive.PWM",
                side_effect=[
                    left_pwm,
                    right_pwm,
                ],
            ),
            patch(
                "betabox_robotics.hardware.servo.PWM",
                return_value=steering_pwm,
            ),
            patch(
                "betabox_robotics.drive.drive.Pin",
                side_effect=[
                    left_pin,
                    right_pin,
                ],
            ),
        ):
            drive = Drive.default(
                config,
                left_reversed=True,
                right_reversed=False,
                left_trim=0.8,
                right_trim=0.7,
                steering_min=-20,
                steering_max=25,
                steering_offset=-2,
            )

        self.assertTrue(
            drive.left_motor.reversed,
        )
        self.assertFalse(
            drive.right_motor.reversed,
        )

        self.assertEqual(
            drive.steering.min_angle,
            -20.0,
        )
        self.assertEqual(
            drive.steering.max_angle,
            25.0,
        )
        self.assertEqual(
            drive.steering.offset,
            -2.0,
        )

        self.assertEqual(
            drive.left_trim,
            0.8,
        )
        self.assertEqual(
            drive.right_trim,
            0.7,
        )

    def test_default_closes_left_motor_when_right_motor_fails(
        self,
    ) -> None:
        config = make_drive_config()
        left_motor = make_motor()

        failure = MotorError("right motor failed")

        with (
            patch(
                "betabox_robotics.drive.drive.PWM",
                side_effect=[
                    MagicMock(spec=PWM),
                    MagicMock(spec=PWM),
                ],
            ),
            patch(
                "betabox_robotics.drive.drive.Pin",
                side_effect=[
                    MagicMock(spec=Pin),
                    MagicMock(spec=Pin),
                ],
            ),
            patch(
                "betabox_robotics.drive.drive.Motor",
                side_effect=[
                    left_motor,
                    failure,
                ],
            ),
            self.assertRaisesRegex(
                MotorError,
                "right motor failed",
            ),
        ):
            Drive.default(config)

        left_motor.close.assert_called_once_with()

    def test_default_closes_motors_when_steering_fails(
        self,
    ) -> None:
        config = make_drive_config()
        left_motor = make_motor()
        right_motor = make_motor()

        failure = HardwareError("steering failed")

        with (
            patch(
                "betabox_robotics.drive.drive.PWM",
                side_effect=[
                    MagicMock(spec=PWM),
                    MagicMock(spec=PWM),
                ],
            ),
            patch(
                "betabox_robotics.drive.drive.Pin",
                side_effect=[
                    MagicMock(spec=Pin),
                    MagicMock(spec=Pin),
                ],
            ),
            patch(
                "betabox_robotics.drive.drive.Motor",
                side_effect=[
                    left_motor,
                    right_motor,
                ],
            ),
            patch(
                "betabox_robotics.drive.drive.Servo",
                side_effect=failure,
            ),
            self.assertRaisesRegex(
                HardwareError,
                "steering failed",
            ),
        ):
            Drive.default(config)

        right_motor.close.assert_called_once_with()
        left_motor.close.assert_called_once_with()

    def test_default_closes_all_components_when_drive_init_fails(
        self,
    ) -> None:
        config = make_drive_config()

        (
            left_pwm,
            right_pwm,
            steering_pwm,
            left_pin,
            right_pin,
        ) = make_factory_hardware()

        with (
            patch(
                "betabox_robotics.drive.drive.PWM",
                side_effect=[
                    left_pwm,
                    right_pwm,
                ],
            ),
            patch(
                "betabox_robotics.hardware.servo.PWM",
                return_value=steering_pwm,
            ),
            patch(
                "betabox_robotics.drive.drive.Pin",
                side_effect=[
                    left_pin,
                    right_pin,
                ],
            ),
            self.assertRaisesRegex(
                TypeError,
                "left_trim must be a number",
            ),
        ):
            Drive.default(
                config,
                left_trim="invalid",  # type: ignore[arg-type]
            )

        left_pwm.close.assert_called_once_with()
        left_pin.close.assert_called_once_with()

        right_pwm.close.assert_called_once_with()
        right_pin.close.assert_called_once_with()

        steering_pwm.close.assert_called_once_with()


class DriveMovementTests(unittest.TestCase):
    def test_speed_sets_both_motor_targets(
        self,
    ) -> None:
        drive, left, right, _ = make_drive()

        drive.speed(
            30,
            -40,
        )

        left.set_speed.assert_called_once_with(
            30.0,
            smooth=True,
        )
        right.set_speed.assert_called_once_with(
            -40.0,
            smooth=True,
        )

    def test_speed_applies_trim(
        self,
    ) -> None:
        drive, left, right, _ = make_drive(
            left_trim=0.8,
            right_trim=0.5,
        )

        drive.speed(
            50,
            -40,
            smooth=False,
        )

        left.set_speed.assert_called_once_with(
            40.0,
            smooth=False,
        )
        right.set_speed.assert_called_once_with(
            -20.0,
            smooth=False,
        )

    def test_speed_clamps_trimmed_targets(
        self,
    ) -> None:
        drive, left, right, _ = make_drive(
            left_trim=2.0,
            right_trim=3.0,
        )

        drive.speed(
            80,
            -80,
            smooth=False,
        )

        left.set_speed.assert_called_once_with(
            100.0,
            smooth=False,
        )
        right.set_speed.assert_called_once_with(
            -100.0,
            smooth=False,
        )

    def test_speed_rejects_invalid_smooth_type(
        self,
    ) -> None:
        drive, _, _, _ = make_drive()

        with self.assertRaisesRegex(
            TypeError,
            "smooth must be a boolean",
        ):
            drive.speed(
                20,
                20,
                smooth=1,  # type: ignore[arg-type]
            )

    def test_speed_rejects_boolean_speed(
        self,
    ) -> None:
        drive, _, _, _ = make_drive()

        with self.assertRaisesRegex(
            TypeError,
            "speed must be a number",
        ):
            drive.speed(
                True,
                20,
            )

    def test_speed_rejects_out_of_range_value(
        self,
    ) -> None:
        drive, _, _, _ = make_drive()

        with self.assertRaisesRegex(
            DriveError,
            "between -100 and 100",
        ):
            drive.speed(
                101,
                0,
            )

    def test_speed_rejects_non_finite_value(
        self,
    ) -> None:
        drive, _, _, _ = make_drive()

        with self.assertRaisesRegex(
            ValueError,
            "speed must be finite",
        ):
            drive.speed(
                math.inf,
                0,
            )

    def test_speed_emergency_stops_both_motors_if_left_fails(
        self,
    ) -> None:
        drive, left, right, _ = make_drive()

        left.set_speed.side_effect = MotorError("left failure")

        with self.assertRaisesRegex(
            MotorError,
            "left failure",
        ):
            drive.speed(
                20,
                20,
            )

        left.emergency_stop.assert_called_once_with()
        right.emergency_stop.assert_called_once_with()

    def test_speed_emergency_stops_both_motors_if_right_fails(
        self,
    ) -> None:
        drive, left, right, _ = make_drive()

        right.set_speed.side_effect = MotorError("right failure")

        with self.assertRaisesRegex(
            MotorError,
            "right failure",
        ):
            drive.speed(
                20,
                20,
            )

        left.set_speed.assert_called_once()
        left.emergency_stop.assert_called_once_with()
        right.emergency_stop.assert_called_once_with()

    def test_forward_uses_positive_equal_speeds(
        self,
    ) -> None:
        drive, _, _, _ = make_drive()

        with patch.object(
            drive,
            "speed",
        ) as speed:
            drive.forward(
                -35,
                smooth=False,
            )

        speed.assert_called_once_with(
            35.0,
            35.0,
            smooth=False,
        )

    def test_backward_uses_negative_equal_speeds(
        self,
    ) -> None:
        drive, _, _, _ = make_drive()

        with patch.object(
            drive,
            "speed",
        ) as speed:
            drive.backward(
                -35,
                smooth=False,
            )

        speed.assert_called_once_with(
            -35.0,
            -35.0,
            smooth=False,
        )


class DriveSteeringTests(unittest.TestCase):
    def test_left_uses_negative_angle(
        self,
    ) -> None:
        drive, _, _, steering = make_drive()

        drive.left(
            -20,
            smooth=False,
        )

        steering.move_to.assert_called_once_with(
            -20.0,
            smooth=False,
        )

    def test_right_uses_positive_angle(
        self,
    ) -> None:
        drive, _, _, steering = make_drive()

        drive.right(
            -20,
            smooth=False,
        )

        steering.move_to.assert_called_once_with(
            20.0,
            smooth=False,
        )

    def test_center_moves_to_logical_zero(
        self,
    ) -> None:
        drive, _, _, steering = make_drive()

        drive.center(smooth=False)

        steering.move_to.assert_called_once_with(
            0,
            smooth=False,
        )

    def test_steering_rejects_boolean_angle(
        self,
    ) -> None:
        drive, _, _, _ = make_drive()

        with self.assertRaisesRegex(
            TypeError,
            "angle must be a number",
        ):
            drive.left(True)


class DriveStopTests(unittest.TestCase):
    def test_stop_calls_controlled_stop_on_both_motors(
        self,
    ) -> None:
        drive, left, right, _ = make_drive()

        drive.stop()

        left.stop.assert_called_once_with()
        right.stop.assert_called_once_with()

        left.emergency_stop.assert_not_called()
        right.emergency_stop.assert_not_called()

    def test_stop_attempts_right_motor_when_left_stop_fails(
        self,
    ) -> None:
        drive, left, right, _ = make_drive()

        left.stop.side_effect = MotorError("left stop failed")

        with self.assertRaisesRegex(
            MotorError,
            "left stop failed",
        ):
            drive.stop()

        right.stop.assert_called_once_with()

        left.emergency_stop.assert_called_once_with()
        right.emergency_stop.assert_called_once_with()

    def test_stop_preserves_first_error(
        self,
    ) -> None:
        drive, left, right, _ = make_drive()

        first = MotorError("left stop failed")
        second = MotorError("right stop failed")

        left.stop.side_effect = first
        right.stop.side_effect = second

        with self.assertRaises(MotorError) as raised:
            drive.stop()

        self.assertIs(
            raised.exception,
            first,
        )

    def test_emergency_stop_calls_both_motors(
        self,
    ) -> None:
        drive, left, right, _ = make_drive()

        drive.emergency_stop()

        left.emergency_stop.assert_called_once_with()
        right.emergency_stop.assert_called_once_with()

    def test_emergency_stop_attempts_both_and_raises_first_error(
        self,
    ) -> None:
        drive, left, right, _ = make_drive()

        first = MotorError("left emergency stop failed")
        second = MotorError("right emergency stop failed")

        left.emergency_stop.side_effect = first
        right.emergency_stop.side_effect = second

        with self.assertRaises(MotorError) as raised:
            drive.emergency_stop()

        self.assertIs(
            raised.exception,
            first,
        )

        right.emergency_stop.assert_called_once_with()


class DriveLifecycleTests(unittest.TestCase):
    def test_status_reports_current_configuration(
        self,
    ) -> None:
        drive, _, _, steering = make_drive(
            left_trim=0.8,
            right_trim=0.9,
        )
        steering.offset = 4.0

        status = drive.status()

        self.assertEqual(
            status,
            DriveStatus(
                closed=False,
                left_trim=0.8,
                right_trim=0.9,
                steering_offset=4.0,
            ),
        )

    def test_close_emergency_stops_and_closes_all_components(
        self,
    ) -> None:
        drive, left, right, steering = make_drive()

        drive.close()

        left.emergency_stop.assert_called_once_with()
        right.emergency_stop.assert_called_once_with()

        left.close.assert_called_once_with()
        right.close.assert_called_once_with()
        steering.close.assert_called_once_with()

        self.assertTrue(
            drive.closed,
        )

    def test_close_skips_emergency_stop_for_closed_motor(
        self,
    ) -> None:
        drive, left, right, _ = make_drive()
        left.closed = True

        drive.close()

        left.emergency_stop.assert_not_called()
        right.emergency_stop.assert_called_once_with()

    def test_close_is_idempotent(
        self,
    ) -> None:
        drive, left, right, steering = make_drive()

        drive.close()
        drive.close()

        left.close.assert_called_once_with()
        right.close.assert_called_once_with()
        steering.close.assert_called_once_with()

    def test_close_marks_drive_closed_when_cleanup_fails(
        self,
    ) -> None:
        drive, left, right, steering = make_drive()

        left.close.side_effect = OSError("left close failed")

        with self.assertRaisesRegex(
            OSError,
            "left close failed",
        ):
            drive.close()

        right.close.assert_called_once_with()
        steering.close.assert_called_once_with()

        self.assertTrue(
            drive.closed,
        )

    def test_operations_reject_closed_drive(
        self,
    ) -> None:
        drive, _, _, _ = make_drive()
        drive.close()

        operations = (
            lambda: drive.speed(10, 10),
            lambda: drive.forward(),
            lambda: drive.backward(),
            lambda: drive.left(),
            lambda: drive.right(),
            lambda: drive.center(),
            lambda: drive.stop(),
            lambda: drive.emergency_stop(),
        )

        for operation in operations:
            with (
                self.subTest(
                    operation=operation,
                ),
                self.assertRaisesRegex(
                    DriveError,
                    "drive subsystem is closed",
                ),
            ):
                operation()

    def test_deinit_delegates_to_close(
        self,
    ) -> None:
        drive, left, right, steering = make_drive()

        drive.deinit()

        left.close.assert_called_once_with()
        right.close.assert_called_once_with()
        steering.close.assert_called_once_with()
        self.assertTrue(
            drive.closed,
        )

    def test_context_manager_returns_self_and_closes(
        self,
    ) -> None:
        drive, left, right, steering = make_drive()

        with drive as entered:
            self.assertIs(
                entered,
                drive,
            )
            self.assertFalse(
                drive.closed,
            )

        left.close.assert_called_once_with()
        right.close.assert_called_once_with()
        steering.close.assert_called_once_with()
        self.assertTrue(
            drive.closed,
        )

    def test_closed_drive_cannot_reenter_context(
        self,
    ) -> None:
        drive, _, _, _ = make_drive()
        drive.close()

        with (
            self.assertRaisesRegex(
                DriveError,
                "drive subsystem is closed",
            ),
            drive,
        ):
            pass


if __name__ == "__main__":
    unittest.main()
