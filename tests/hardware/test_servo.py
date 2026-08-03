from __future__ import annotations

import math
import unittest
from unittest.mock import MagicMock, call, patch

from betabox_robotics.hardware.board import (
    Pins,
    PWMChannel,
)
from betabox_robotics.hardware.pwm import PWM
from betabox_robotics.hardware.servo import (
    Servo,
    ServoError,
    map_range,
)


class ServoTests(unittest.TestCase):
    def make_servo(
        self,
        *,
        min_angle: float = -90,
        max_angle: float = 90,
        offset: float = 0,
        max_step: float = 2,
        step_delay: float = 0,
    ) -> tuple[Servo, MagicMock]:
        pwm = MagicMock(spec=PWM)
        pwm.CLOCK = PWM.CLOCK

        with patch(
            "betabox_robotics.hardware.servo.PWM",
            return_value=pwm,
        ):
            servo = Servo(
                Pins.P0,
                min_angle=min_angle,
                max_angle=max_angle,
                offset=offset,
                max_step=max_step,
                step_delay=step_delay,
            )

        pwm.reset_mock()

        return servo, pwm

    def test_constructor_creates_and_configures_pwm(
        self,
    ) -> None:
        pwm = MagicMock(spec=PWM)
        pwm.CLOCK = PWM.CLOCK

        addresses = (
            0x14,
            0x15,
        )

        with patch(
            "betabox_robotics.hardware.servo.PWM",
            return_value=pwm,
        ) as pwm_type:
            servo = Servo(
                PWMChannel.P3,
                address=addresses,
                min_angle=-45,
                max_angle=45,
                offset=3,
                max_step=4,
                step_delay=0.02,
            )

        pwm_type.assert_called_once_with(
            PWMChannel.P3,
            address=addresses,
            bus=None,
        )

        pwm.set_period.assert_called_once_with(Servo.PERIOD)

        expected_prescaler = PWM.CLOCK / Servo.FREQUENCY_HZ / Servo.PERIOD

        pwm.set_prescaler.assert_called_once_with(expected_prescaler)

        self.assertEqual(
            servo.min_angle,
            -45.0,
        )
        self.assertEqual(
            servo.max_angle,
            45.0,
        )
        self.assertEqual(
            servo.offset,
            3.0,
        )
        self.assertEqual(
            servo.max_step,
            4.0,
        )
        self.assertEqual(
            servo.step_delay,
            0.02,
        )
        self.assertIsNone(servo.get_angle())
        self.assertIsNone(servo.physical_angle)
        self.assertFalse(servo.closed)

    def test_constructor_forwards_borrowed_i2c_bus(
        self,
    ) -> None:
        pwm = MagicMock(spec=PWM)
        pwm.CLOCK = PWM.CLOCK
        bus = MagicMock()

        with patch(
            "betabox_robotics.hardware.servo.PWM",
            return_value=pwm,
        ) as pwm_type:
            Servo(
                Pins.P0,
                bus=bus,
            )

        pwm_type.assert_called_once_with(
            Pins.P0,
            address=None,
            bus=bus,
        )

    def test_constructor_rejects_equal_angle_limits(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ServoError,
            "min_angle must be less than max_angle",
        ):
            Servo(
                Pins.P0,
                min_angle=30,
                max_angle=30,
            )

    def test_constructor_rejects_reversed_angle_limits(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ServoError,
            "min_angle must be less than max_angle",
        ):
            Servo(
                Pins.P0,
                min_angle=45,
                max_angle=-45,
            )

    def test_constructor_rejects_minimum_below_supported_range(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ServoError,
            "min_angle must be between -90 and 90",
        ):
            Servo(
                Pins.P0,
                min_angle=-91,
            )

    def test_constructor_rejects_maximum_above_supported_range(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ServoError,
            "max_angle must be between -90 and 90",
        ):
            Servo(
                Pins.P0,
                max_angle=91,
            )

    def test_constructor_rejects_non_positive_max_step(
        self,
    ) -> None:
        for value in (
            0,
            -1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ServoError,
                    "max_step must be greater than 0",
                ),
            ):
                Servo(
                    Pins.P0,
                    max_step=value,
                )

    def test_constructor_rejects_negative_step_delay(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ServoError,
            "step_delay cannot be negative",
        ):
            Servo(
                Pins.P0,
                step_delay=-0.01,
            )

    def test_constructor_rejects_boolean_numeric_configuration(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "offset must be a number",
        ):
            Servo(
                Pins.P0,
                offset=True,
            )

    def test_constructor_preserves_original_setup_error(
        self,
    ) -> None:
        pwm = MagicMock(spec=PWM)
        pwm.CLOCK = PWM.CLOCK

        setup_error = ServoError("period setup failed")

        pwm.set_period.side_effect = setup_error
        pwm.close.side_effect = OSError("cleanup failed")

        with (
            patch(
                "betabox_robotics.hardware.servo.PWM",
                return_value=pwm,
            ),
            self.assertRaisesRegex(
                ServoError,
                "period setup failed",
            ) as raised,
        ):
            Servo(Pins.P0)

        self.assertIs(
            raised.exception,
            setup_error,
        )

    def test_require_finite_number_accepts_int_and_float(
        self,
    ) -> None:
        self.assertEqual(
            Servo._require_finite_number(
                5,
                name="value",
            ),
            5.0,
        )

        self.assertEqual(
            Servo._require_finite_number(
                2.5,
                name="value",
            ),
            2.5,
        )

    def test_require_finite_number_rejects_boolean(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "value must be a number",
        ):
            Servo._require_finite_number(
                True,
                name="value",
            )

    def test_require_finite_number_rejects_non_numeric_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "value must be a number",
        ):
            Servo._require_finite_number(
                "5",
                name="value",
            )

    def test_require_finite_number_rejects_nan(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "value must be finite",
        ):
            Servo._require_finite_number(
                math.nan,
                name="value",
            )

    def test_require_finite_number_rejects_infinity(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "value must be finite",
        ):
            Servo._require_finite_number(
                math.inf,
                name="value",
            )

    def test_map_range_maps_midpoint(
        self,
    ) -> None:
        self.assertEqual(
            map_range(
                0,
                -90,
                90,
                500,
                2500,
            ),
            1500,
        )

    def test_map_range_maps_endpoints(
        self,
    ) -> None:
        self.assertEqual(
            map_range(
                -90,
                -90,
                90,
                500,
                2500,
            ),
            500,
        )

        self.assertEqual(
            map_range(
                90,
                -90,
                90,
                500,
                2500,
            ),
            2500,
        )

    def test_map_range_rejects_zero_width_input_range(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "input range cannot have equal",
        ):
            map_range(
                1,
                5,
                5,
                0,
                10,
            )

    def test_angle_to_pulse_width_mapping(
        self,
    ) -> None:
        self.assertEqual(
            Servo._angle_to_pulse_us(-90),
            Servo.MIN_PULSE_US,
        )
        self.assertEqual(
            Servo._angle_to_pulse_us(0),
            1500.0,
        )
        self.assertEqual(
            Servo._angle_to_pulse_us(90),
            Servo.MAX_PULSE_US,
        )

    def test_clamp_limits_values(
        self,
    ) -> None:
        self.assertEqual(
            Servo._clamp(
                120,
                -90,
                90,
            ),
            90,
        )
        self.assertEqual(
            Servo._clamp(
                -120,
                -90,
                90,
            ),
            -90,
        )
        self.assertEqual(
            Servo._clamp(
                20,
                -90,
                90,
            ),
            20,
        )

    def test_move_to_without_existing_position_moves_immediately(
        self,
    ) -> None:
        servo, _ = self.make_servo(
            offset=5,
        )

        with patch.object(
            servo,
            "_move_immediate",
        ) as move_immediate:
            servo.move_to(10)

        move_immediate.assert_called_once_with(15.0)

    def test_move_to_applies_offset_and_tracks_both_angles(
        self,
    ) -> None:
        servo, _ = self.make_servo(
            offset=5,
        )

        with patch.object(
            servo,
            "set_pulse_width_us",
        ):
            servo.move_to(
                10,
                smooth=False,
            )

        self.assertEqual(
            servo.get_angle(),
            10.0,
        )
        self.assertEqual(
            servo.physical_angle,
            15.0,
        )

    def test_move_to_clamps_to_physical_limits(
        self,
    ) -> None:
        servo, _ = self.make_servo(
            min_angle=-30,
            max_angle=30,
            offset=5,
        )

        with patch.object(
            servo,
            "set_pulse_width_us",
        ):
            servo.move_to(
                100,
                smooth=False,
            )

        self.assertEqual(
            servo.physical_angle,
            30.0,
        )

        # Effective logical angle is physical minus offset.
        self.assertEqual(
            servo.get_angle(),
            25.0,
        )

    def test_move_to_rejects_non_numeric_angle(
        self,
    ) -> None:
        servo, _ = self.make_servo()

        with self.assertRaisesRegex(
            TypeError,
            "angle must be a number",
        ):
            servo.move_to(
                "10"  # type: ignore[arg-type]
            )

    def test_move_to_rejects_boolean_angle(
        self,
    ) -> None:
        servo, _ = self.make_servo()

        with self.assertRaisesRegex(
            TypeError,
            "angle must be a number",
        ):
            servo.move_to(True)

    def test_move_to_rejects_invalid_smooth_type(
        self,
    ) -> None:
        servo, _ = self.make_servo()

        with self.assertRaisesRegex(
            TypeError,
            "smooth must be a boolean",
        ):
            servo.move_to(
                10,
                smooth=1,  # type: ignore[arg-type]
            )

    def test_smooth_move_uses_configured_steps(
        self,
    ) -> None:
        servo, _ = self.make_servo(
            max_step=10,
            step_delay=0,
        )

        servo._physical_angle = 0.0
        servo._angle = 0.0

        with (
            patch.object(
                servo,
                "_write_physical_angle",
            ) as write_physical,
            patch.object(
                servo,
                "_move_immediate",
            ) as move_immediate,
        ):
            servo.move_to(
                25,
                smooth=True,
            )

        self.assertEqual(
            write_physical.call_args_list,
            [
                call(10.0),
                call(20.0),
            ],
        )

        move_immediate.assert_called_once_with(25.0)

    def test_smooth_move_uses_configured_delay(
        self,
    ) -> None:
        servo, _ = self.make_servo(
            max_step=10,
            step_delay=0.05,
        )

        servo._physical_angle = 0.0
        servo._angle = 0.0

        with (
            patch.object(
                servo,
                "_write_physical_angle",
            ),
            patch.object(
                servo,
                "_move_immediate",
            ),
            patch("betabox_robotics.hardware.servo.sleep") as sleep_mock,
        ):
            servo.move_to(25)

        self.assertEqual(
            sleep_mock.call_count,
            2,
        )
        sleep_mock.assert_called_with(0.05)

    def test_smooth_move_skips_delay_when_zero(
        self,
    ) -> None:
        servo, _ = self.make_servo(
            max_step=10,
            step_delay=0,
        )

        servo._physical_angle = 0.0
        servo._angle = 0.0

        with (
            patch.object(
                servo,
                "_write_physical_angle",
            ),
            patch.object(
                servo,
                "_move_immediate",
            ),
            patch("betabox_robotics.hardware.servo.sleep") as sleep_mock,
        ):
            servo.move_to(25)

        sleep_mock.assert_not_called()

    def test_center_moves_to_logical_zero(
        self,
    ) -> None:
        servo, _ = self.make_servo()

        with patch.object(
            servo,
            "move_to",
        ) as move_to:
            servo.center()

        move_to.assert_called_once_with(0)

    def test_min_reaches_exact_physical_minimum(
        self,
    ) -> None:
        servo, _ = self.make_servo(
            min_angle=-30,
            max_angle=30,
            offset=5,
        )

        with patch.object(
            servo,
            "move_to",
        ) as move_to:
            servo.min()

        move_to.assert_called_once_with(-35.0)

    def test_max_reaches_exact_physical_maximum(
        self,
    ) -> None:
        servo, _ = self.make_servo(
            min_angle=-30,
            max_angle=30,
            offset=5,
        )

        with patch.object(
            servo,
            "move_to",
        ) as move_to:
            servo.max()

        move_to.assert_called_once_with(25.0)

    def test_write_physical_angle_updates_position(
        self,
    ) -> None:
        servo, _ = self.make_servo()

        with patch.object(
            servo,
            "set_pulse_width_us",
        ) as set_pulse:
            servo._write_physical_angle(0)

        set_pulse.assert_called_once_with(1500.0)
        self.assertEqual(servo.physical_angle, 0)

    def test_set_pulse_width_us_converts_to_pwm_period_value(
        self,
    ) -> None:
        servo, pwm = self.make_servo()

        servo.set_pulse_width_us(1500)

        expected = int((1500 / 20_000.0) * Servo.PERIOD)

        pwm.set_pulse_width.assert_called_once_with(expected)

    def test_set_pulse_width_us_clamps_low_value(
        self,
    ) -> None:
        servo, pwm = self.make_servo()

        servo.set_pulse_width_us(100)

        expected = int((Servo.MIN_PULSE_US / 20_000.0) * Servo.PERIOD)

        pwm.set_pulse_width.assert_called_once_with(expected)

    def test_set_pulse_width_us_clamps_high_value(
        self,
    ) -> None:
        servo, pwm = self.make_servo()

        servo.set_pulse_width_us(5000)

        expected = int((Servo.MAX_PULSE_US / 20_000.0) * Servo.PERIOD)

        pwm.set_pulse_width.assert_called_once_with(expected)

    def test_set_pulse_width_us_rejects_invalid_type(
        self,
    ) -> None:
        servo, _ = self.make_servo()

        with self.assertRaisesRegex(
            TypeError,
            "pulse_us must be a number",
        ):
            servo.set_pulse_width_us(
                "1500"  # type: ignore[arg-type]
            )

    def test_angle_alias_gets_current_angle(
        self,
    ) -> None:
        servo, _ = self.make_servo()
        servo._angle = 12.0

        self.assertEqual(
            servo.angle(),
            12.0,
        )

    def test_angle_alias_sets_angle(
        self,
    ) -> None:
        servo, _ = self.make_servo()

        with patch.object(
            servo,
            "move_to",
        ) as move_to:
            result = servo.angle(20)

        self.assertIsNone(result)
        move_to.assert_called_once_with(20)

    def test_pulse_width_time_delegates(
        self,
    ) -> None:
        servo, _ = self.make_servo()

        with patch.object(
            servo,
            "set_pulse_width_us",
        ) as set_pulse:
            servo.pulse_width_time(1500)

        set_pulse.assert_called_once_with(1500)

    def test_pwm_property_rejects_closed_servo(
        self,
    ) -> None:
        servo, _ = self.make_servo()
        servo.close()

        with self.assertRaisesRegex(
            ServoError,
            "PWM has been closed",
        ):
            _ = servo.pwm

    def test_close_closes_pwm_and_clears_positions(
        self,
    ) -> None:
        servo, pwm = self.make_servo()
        servo._angle = 10.0
        servo._physical_angle = 15.0

        servo.close()

        pwm.close.assert_called_once_with()
        self.assertTrue(servo.closed)
        self.assertIsNone(servo.get_angle())
        self.assertIsNone(servo.physical_angle)

    def test_close_is_idempotent(
        self,
    ) -> None:
        servo, pwm = self.make_servo()

        servo.close()
        servo.close()

        pwm.close.assert_called_once_with()

    def test_close_clears_state_when_pwm_close_fails(
        self,
    ) -> None:
        servo, pwm = self.make_servo()
        servo._angle = 10.0
        servo._physical_angle = 10.0

        pwm.close.side_effect = OSError("close failed")

        with self.assertRaisesRegex(
            OSError,
            "close failed",
        ):
            servo.close()

        self.assertTrue(servo.closed)
        self.assertIsNone(servo.get_angle())
        self.assertIsNone(servo.physical_angle)

    def test_deinit_delegates_to_close(
        self,
    ) -> None:
        servo, pwm = self.make_servo()

        servo.deinit()

        pwm.close.assert_called_once_with()
        self.assertTrue(servo.closed)

    def test_context_manager_returns_self_and_closes(
        self,
    ) -> None:
        servo, pwm = self.make_servo()

        with servo as entered:
            self.assertIs(
                entered,
                servo,
            )
            self.assertFalse(servo.closed)

        pwm.close.assert_called_once_with()
        self.assertTrue(servo.closed)

    def test_closed_servo_cannot_reenter_context(
        self,
    ) -> None:
        servo, _ = self.make_servo()
        servo.close()

        with (
            self.assertRaisesRegex(
                ServoError,
                "closed Servo",
            ),
            servo,
        ):
            pass


if __name__ == "__main__":
    unittest.main()
