from __future__ import annotations

import math
import unittest
from unittest.mock import MagicMock, patch

from betabox_robotics.hardware.motor import (
    Motor,
    MotorError,
    MotorMode,
)
from betabox_robotics.hardware.pin import Pin
from betabox_robotics.hardware.pwm import PWM


def make_pwm() -> MagicMock:
    return MagicMock(spec=PWM)


def make_pin() -> MagicMock:
    return MagicMock(spec=Pin)


class MotorTests(unittest.TestCase):
    def make_pwm_dir_motor(
        self,
        *,
        reversed: bool = False,
        frequency: float = 100.0,
        max_step: float = 5.0,
        step_delay: float = 0.01,
    ) -> tuple[Motor, MagicMock, MagicMock]:
        pwm = make_pwm()
        direction = make_pin()

        motor = Motor(
            pwm,
            direction,
            reversed=reversed,
            mode=MotorMode.PWM_DIR,
            frequency=frequency,
            max_step=max_step,
            step_delay=step_delay,
        )

        pwm.reset_mock()
        direction.reset_mock()

        return motor, pwm, direction

    def make_pwm_pwm_motor(
        self,
        *,
        reversed: bool = False,
        frequency: float = 100.0,
        max_step: float = 5.0,
        step_delay: float = 0.01,
    ) -> tuple[Motor, MagicMock, MagicMock]:
        pwm_a = make_pwm()
        pwm_b = make_pwm()

        motor = Motor(
            pwm_a,
            pwm_b,
            reversed=reversed,
            mode=MotorMode.PWM_PWM,
            frequency=frequency,
            max_step=max_step,
            step_delay=step_delay,
        )

        pwm_a.reset_mock()
        pwm_b.reset_mock()

        return motor, pwm_a, pwm_b

    def test_pwm_dir_constructor_initializes_outputs(
        self,
    ) -> None:
        pwm = make_pwm()
        direction = make_pin()

        motor = Motor(
            pwm,
            direction,
            mode=MotorMode.PWM_DIR,
            frequency=125,
        )

        pwm.set_frequency.assert_called_once_with(125.0)
        pwm.set_duty_cycle.assert_called_once_with(0)
        direction.write.assert_called_once_with(False)

        self.assertIs(
            motor.mode,
            MotorMode.PWM_DIR,
        )
        self.assertEqual(
            motor.get_speed(),
            0.0,
        )
        self.assertFalse(
            motor.closed,
        )

    def test_pwm_pwm_constructor_initializes_both_outputs(
        self,
    ) -> None:
        pwm_a = make_pwm()
        pwm_b = make_pwm()

        motor = Motor(
            pwm_a,
            pwm_b,
            mode=MotorMode.PWM_PWM,
            frequency=125,
        )

        pwm_a.set_frequency.assert_called_once_with(125.0)
        pwm_b.set_frequency.assert_called_once_with(125.0)

        pwm_a.set_duty_cycle.assert_called_once_with(0)
        pwm_b.set_duty_cycle.assert_called_once_with(0)

        self.assertIs(
            motor.mode,
            MotorMode.PWM_PWM,
        )
        self.assertFalse(
            motor.closed,
        )

    def test_rejects_invalid_mode_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "mode must be",
        ):
            Motor(
                make_pwm(),
                make_pin(),
                mode="PWM_DIR",  # type: ignore[arg-type]
            )

    def test_rejects_non_boolean_reversed(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "reversed must be a boolean",
        ):
            Motor(
                make_pwm(),
                make_pin(),
                reversed=1,  # type: ignore[arg-type]
            )

    def test_pwm_dir_requires_pwm_instance(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "pwm must be a PWM instance",
        ):
            Motor(
                object(),  # type: ignore[arg-type]
                make_pin(),
                mode=MotorMode.PWM_DIR,
            )

    def test_pwm_dir_requires_pin_direction(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "direction must be a Pin instance",
        ):
            Motor(
                make_pwm(),
                make_pwm(),
                mode=MotorMode.PWM_DIR,
            )

    def test_pwm_pwm_requires_second_pwm(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "direction must be a PWM instance",
        ):
            Motor(
                make_pwm(),
                make_pin(),
                mode=MotorMode.PWM_PWM,
            )

    def test_rejects_zero_frequency(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            MotorError,
            "frequency must be greater than 0",
        ):
            Motor(
                make_pwm(),
                make_pin(),
                frequency=0,
            )

    def test_rejects_non_positive_max_step(
        self,
    ) -> None:
        for value in (
            0,
            -1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    MotorError,
                    "max_step must be greater than 0",
                ),
            ):
                Motor(
                    make_pwm(),
                    make_pin(),
                    max_step=value,
                )

    def test_rejects_negative_step_delay(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            MotorError,
            "step_delay cannot be negative",
        ):
            Motor(
                make_pwm(),
                make_pin(),
                step_delay=-0.01,
            )

    def test_require_finite_number_accepts_numbers(
        self,
    ) -> None:
        self.assertEqual(
            Motor._require_finite_number(
                5,
                name="value",
            ),
            5.0,
        )

        self.assertEqual(
            Motor._require_finite_number(
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
            "must be a number",
        ):
            Motor._require_finite_number(
                True,
                name="value",
            )

    def test_require_finite_number_rejects_non_numeric_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "must be a number",
        ):
            Motor._require_finite_number(
                "5",
                name="value",
            )

    def test_require_finite_number_rejects_nan(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "must be finite",
        ):
            Motor._require_finite_number(
                math.nan,
                name="value",
            )

    def test_require_finite_number_rejects_infinity(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "must be finite",
        ):
            Motor._require_finite_number(
                math.inf,
                name="value",
            )

    def test_clamp_limits_value(
        self,
    ) -> None:
        self.assertEqual(
            Motor._clamp(
                120,
                -100,
                100,
            ),
            100,
        )

        self.assertEqual(
            Motor._clamp(
                -120,
                -100,
                100,
            ),
            -100,
        )

        self.assertEqual(
            Motor._clamp(
                25,
                -100,
                100,
            ),
            25,
        )

    def test_set_speed_rejects_invalid_smooth_type(
        self,
    ) -> None:
        motor, _, _ = self.make_pwm_dir_motor()

        with self.assertRaisesRegex(
            TypeError,
            "smooth must be a boolean",
        ):
            motor.set_speed(
                25,
                smooth=1,  # type: ignore[arg-type]
            )

    def test_set_speed_rejects_boolean_speed(
        self,
    ) -> None:
        motor, _, _ = self.make_pwm_dir_motor()

        with self.assertRaisesRegex(
            TypeError,
            "speed must be a number",
        ):
            motor.set_speed(True)

    def test_set_speed_clamps_positive_value(
        self,
    ) -> None:
        motor, pwm, direction = self.make_pwm_dir_motor()

        motor.set_speed(
            150,
            smooth=False,
        )

        direction.write.assert_called_once_with(True)
        pwm.set_duty_cycle.assert_called_once_with(100.0)

        self.assertEqual(
            motor.get_speed(),
            100.0,
        )

    def test_set_speed_clamps_negative_value(
        self,
    ) -> None:
        motor, pwm, direction = self.make_pwm_dir_motor()

        motor.set_speed(
            -150,
            smooth=False,
        )

        direction.write.assert_called_once_with(False)
        pwm.set_duty_cycle.assert_called_once_with(100.0)

        self.assertEqual(
            motor.get_speed(),
            -100.0,
        )

    def test_pwm_dir_forward_sets_direction_then_duty(
        self,
    ) -> None:
        motor, pwm, direction = self.make_pwm_dir_motor()

        events: list[tuple[str, object]] = []

        direction.write.side_effect = lambda value: events.append(
            (
                "direction",
                value,
            )
        )

        pwm.set_duty_cycle.side_effect = lambda value: events.append(
            (
                "duty",
                value,
            )
        )

        motor.set_speed(
            30,
            smooth=False,
        )

        self.assertEqual(
            events,
            [
                (
                    "direction",
                    True,
                ),
                (
                    "duty",
                    30.0,
                ),
            ],
        )

        self.assertEqual(
            motor.get_speed(),
            30.0,
        )

    def test_pwm_dir_backward_sets_reverse_direction(
        self,
    ) -> None:
        motor, pwm, direction = self.make_pwm_dir_motor()

        motor.set_speed(
            -30,
            smooth=False,
        )

        direction.write.assert_called_once_with(False)
        pwm.set_duty_cycle.assert_called_once_with(30.0)

        self.assertEqual(
            motor.get_speed(),
            -30.0,
        )

    def test_reversed_pwm_dir_inverts_direction(
        self,
    ) -> None:
        motor, pwm, direction = self.make_pwm_dir_motor(reversed=True)

        motor.set_speed(
            30,
            smooth=False,
        )

        direction.write.assert_called_once_with(False)
        pwm.set_duty_cycle.assert_called_once_with(30.0)

    def test_pwm_dir_zero_preserves_direction_pin(
        self,
    ) -> None:
        motor, pwm, direction = self.make_pwm_dir_motor()

        motor.set_speed(
            30,
            smooth=False,
        )

        pwm.reset_mock()
        direction.reset_mock()

        motor.set_speed(
            0,
            smooth=False,
        )

        pwm.set_duty_cycle.assert_called_once_with(0)
        direction.write.assert_not_called()

        self.assertEqual(
            motor.get_speed(),
            0.0,
        )

    def test_pwm_dir_deenergizes_before_reversal(
        self,
    ) -> None:
        motor, pwm, direction = self.make_pwm_dir_motor()

        motor.set_speed(
            30,
            smooth=False,
        )

        pwm.reset_mock()
        direction.reset_mock()

        events: list[tuple[str, object]] = []

        pwm.set_duty_cycle.side_effect = lambda value: events.append(
            (
                "duty",
                value,
            )
        )

        direction.write.side_effect = lambda value: events.append(
            (
                "direction",
                value,
            )
        )

        motor.set_speed(
            -30,
            smooth=False,
        )

        self.assertEqual(
            events,
            [
                (
                    "duty",
                    0,
                ),
                (
                    "direction",
                    False,
                ),
                (
                    "duty",
                    30.0,
                ),
            ],
        )

    def test_pwm_pwm_forward_disables_reverse_first(
        self,
    ) -> None:
        motor, pwm_a, pwm_b = self.make_pwm_pwm_motor()

        events: list[tuple[str, object]] = []

        pwm_a.set_duty_cycle.side_effect = lambda value: events.append(
            (
                "a",
                value,
            )
        )

        pwm_b.set_duty_cycle.side_effect = lambda value: events.append(
            (
                "b",
                value,
            )
        )

        motor.set_speed(
            40,
            smooth=False,
        )

        self.assertEqual(
            events,
            [
                (
                    "b",
                    0,
                ),
                (
                    "a",
                    40.0,
                ),
            ],
        )

    def test_pwm_pwm_backward_disables_forward_first(
        self,
    ) -> None:
        motor, pwm_a, pwm_b = self.make_pwm_pwm_motor()

        events: list[tuple[str, object]] = []

        pwm_a.set_duty_cycle.side_effect = lambda value: events.append(
            (
                "a",
                value,
            )
        )

        pwm_b.set_duty_cycle.side_effect = lambda value: events.append(
            (
                "b",
                value,
            )
        )

        motor.set_speed(
            -40,
            smooth=False,
        )

        self.assertEqual(
            events,
            [
                (
                    "a",
                    0,
                ),
                (
                    "b",
                    40.0,
                ),
            ],
        )

    def test_pwm_pwm_zero_disables_both_outputs(
        self,
    ) -> None:
        motor, pwm_a, pwm_b = self.make_pwm_pwm_motor()

        motor.set_speed(
            40,
            smooth=False,
        )

        pwm_a.reset_mock()
        pwm_b.reset_mock()

        motor.set_speed(
            0,
            smooth=False,
        )

        pwm_a.set_duty_cycle.assert_called_once_with(0)
        pwm_b.set_duty_cycle.assert_called_once_with(0)

    def test_smooth_speed_ramps_in_configured_steps(
        self,
    ) -> None:
        motor, _, _ = self.make_pwm_dir_motor(
            max_step=10,
            step_delay=0,
        )

        with patch.object(
            motor,
            "_set_speed_immediate",
            wraps=motor._set_speed_immediate,
        ) as immediate:
            motor.set_speed(
                25,
                smooth=True,
            )

        self.assertEqual(
            [call.args[0] for call in immediate.call_args_list],
            [
                10.0,
                20.0,
                25.0,
            ],
        )

    def test_smooth_speed_uses_configured_delay(
        self,
    ) -> None:
        motor, _, _ = self.make_pwm_dir_motor(
            max_step=10,
            step_delay=0.05,
        )

        with patch("betabox_robotics.hardware.motor.sleep") as sleep_mock:
            motor.set_speed(
                25,
                smooth=True,
            )

        self.assertEqual(
            sleep_mock.call_count,
            2,
        )
        sleep_mock.assert_called_with(0.05)

    def test_smooth_speed_skips_sleep_when_delay_is_zero(
        self,
    ) -> None:
        motor, _, _ = self.make_pwm_dir_motor(
            max_step=10,
            step_delay=0,
        )

        with patch("betabox_robotics.hardware.motor.sleep") as sleep_mock:
            motor.set_speed(
                25,
                smooth=True,
            )

        sleep_mock.assert_not_called()

    def test_stop_uses_controlled_ramp(
        self,
    ) -> None:
        motor, _, _ = self.make_pwm_dir_motor()

        with patch.object(
            motor,
            "set_speed",
        ) as set_speed:
            motor.stop()

        set_speed.assert_called_once_with(
            0,
            smooth=True,
        )

    def test_emergency_stop_bypasses_ramp(
        self,
    ) -> None:
        motor, _, _ = self.make_pwm_dir_motor()

        with patch.object(
            motor,
            "_set_speed_immediate",
        ) as immediate:
            motor.emergency_stop()

        immediate.assert_called_once_with(0)

    def test_forward_uses_positive_speed(
        self,
    ) -> None:
        motor, _, _ = self.make_pwm_dir_motor()

        with patch.object(
            motor,
            "set_speed",
        ) as set_speed:
            motor.forward(-30)

        set_speed.assert_called_once_with(30.0)

    def test_backward_uses_negative_speed(
        self,
    ) -> None:
        motor, _, _ = self.make_pwm_dir_motor()

        with patch.object(
            motor,
            "set_speed",
        ) as set_speed:
            motor.backward(-30)

        set_speed.assert_called_once_with(-30.0)

    def test_forward_rejects_non_numeric_speed(
        self,
    ) -> None:
        motor, _, _ = self.make_pwm_dir_motor()

        with self.assertRaisesRegex(
            TypeError,
            "speed must be a number",
        ):
            motor.forward(
                "30"  # type: ignore[arg-type]
            )

    def test_speed_alias_gets_current_speed(
        self,
    ) -> None:
        motor, _, _ = self.make_pwm_dir_motor()
        motor._speed = 25.0

        self.assertEqual(
            motor.speed(),
            25.0,
        )

    def test_speed_alias_sets_speed(
        self,
    ) -> None:
        motor, _, _ = self.make_pwm_dir_motor()

        with patch.object(
            motor,
            "set_speed",
        ) as set_speed:
            result = motor.speed(25)

        self.assertIsNone(result)
        set_speed.assert_called_once_with(25)

    def test_set_reversed_while_stopped(
        self,
    ) -> None:
        motor, _, _ = self.make_pwm_dir_motor()

        motor.set_reversed(True)

        self.assertTrue(motor.reversed)

    def test_set_reversed_rejects_non_boolean(
        self,
    ) -> None:
        motor, _, _ = self.make_pwm_dir_motor()

        with self.assertRaisesRegex(
            TypeError,
            "reversed must be a boolean",
        ):
            motor.set_reversed(
                1  # type: ignore[arg-type]
            )

    def test_set_reversed_rejects_change_while_moving(
        self,
    ) -> None:
        motor, _, _ = self.make_pwm_dir_motor()
        motor._speed = 25.0

        with self.assertRaisesRegex(
            MotorError,
            "must be stopped",
        ):
            motor.set_reversed(True)

    def test_constructor_cleanup_preserves_original_error(
        self,
    ) -> None:
        pwm = make_pwm()
        direction = make_pin()

        initialization_error = MotorError("initialization failed")

        pwm.set_frequency.side_effect = initialization_error
        pwm.set_duty_cycle.side_effect = OSError("cleanup failed")

        with self.assertRaisesRegex(
            MotorError,
            "initialization failed",
        ) as raised:
            Motor(
                pwm,
                direction,
                mode=MotorMode.PWM_DIR,
            )

        self.assertIs(
            raised.exception,
            initialization_error,
        )

    def test_close_pwm_dir_stops_and_closes_devices(
        self,
    ) -> None:
        motor, pwm, direction = self.make_pwm_dir_motor()
        motor._speed = 50.0

        motor.close()

        pwm.set_duty_cycle.assert_called_once_with(0)
        pwm.close.assert_called_once_with()
        direction.close.assert_called_once_with()

        self.assertEqual(
            motor.get_speed(),
            0.0,
        )
        self.assertTrue(
            motor.closed,
        )

    def test_close_pwm_pwm_stops_and_closes_both_outputs(
        self,
    ) -> None:
        motor, pwm_a, pwm_b = self.make_pwm_pwm_motor()
        motor._speed = 50.0

        motor.close()

        pwm_a.set_duty_cycle.assert_called_once_with(0)
        pwm_b.set_duty_cycle.assert_called_once_with(0)

        pwm_a.close.assert_called_once_with()
        pwm_b.close.assert_called_once_with()

        self.assertEqual(
            motor.get_speed(),
            0.0,
        )
        self.assertTrue(
            motor.closed,
        )

    def test_close_is_idempotent(
        self,
    ) -> None:
        motor, pwm, direction = self.make_pwm_dir_motor()

        motor.close()
        motor.close()

        pwm.close.assert_called_once_with()
        direction.close.assert_called_once_with()

    def test_close_marks_motor_closed_when_cleanup_fails(
        self,
    ) -> None:
        motor, pwm, _ = self.make_pwm_dir_motor()
        pwm.set_duty_cycle.side_effect = OSError("stop failed")

        with self.assertRaisesRegex(
            OSError,
            "stop failed",
        ):
            motor.close()

        self.assertTrue(
            motor.closed,
        )
        self.assertEqual(
            motor.get_speed(),
            0.0,
        )

    def test_operations_reject_closed_motor(
        self,
    ) -> None:
        motor, _, _ = self.make_pwm_dir_motor()
        motor.close()

        with self.assertRaisesRegex(
            MotorError,
            "Motor is closed",
        ):
            motor.set_speed(25)

        with self.assertRaisesRegex(
            MotorError,
            "Motor is closed",
        ):
            motor.emergency_stop()

        with self.assertRaisesRegex(
            MotorError,
            "Motor is closed",
        ):
            motor.set_reversed(True)

    def test_deinit_delegates_to_close(
        self,
    ) -> None:
        motor, pwm, direction = self.make_pwm_dir_motor()

        motor.deinit()

        pwm.close.assert_called_once_with()
        direction.close.assert_called_once_with()
        self.assertTrue(
            motor.closed,
        )

    def test_context_manager_returns_self_and_closes(
        self,
    ) -> None:
        motor, pwm, direction = self.make_pwm_dir_motor()

        with motor as entered:
            self.assertIs(
                entered,
                motor,
            )
            self.assertFalse(
                motor.closed,
            )

        pwm.close.assert_called_once_with()
        direction.close.assert_called_once_with()
        self.assertTrue(
            motor.closed,
        )

    def test_closed_motor_cannot_reenter_context(
        self,
    ) -> None:
        motor, _, _ = self.make_pwm_dir_motor()
        motor.close()

        with (
            self.assertRaisesRegex(
                MotorError,
                "Motor is closed",
            ),
            motor,
        ):
            pass


if __name__ == "__main__":
    unittest.main()
