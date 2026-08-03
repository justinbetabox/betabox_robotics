from __future__ import annotations

import math
import unittest
from unittest.mock import MagicMock, patch

from betabox_robotics.hardware.board import (
    Pins,
    PWMChannel,
)
from betabox_robotics.hardware.pwm import (
    PWM,
    TIMER_STATE,
    PWMError,
)


class PWMTests(unittest.TestCase):
    def setUp(self) -> None:
        for state in TIMER_STATE:
            state["period"] = 1

    def test_constructs_from_pwm_channel(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ) as set_frequency:
            pwm = PWM(
                PWMChannel.P0,
                bus=bus,
            )

        self.assertEqual(
            pwm.channel,
            0,
        )
        self.assertEqual(
            pwm.timer_index,
            0,
        )
        self.assertIs(
            pwm._bus(),
            bus,
        )
        self.assertFalse(
            pwm.closed,
        )

        set_frequency.assert_called_once_with(PWM.DEFAULT_FREQUENCY)

    def test_constructs_from_string_channel(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                "P19",
                bus=bus,
            )

        self.assertEqual(
            pwm.channel,
            19,
        )
        self.assertEqual(
            pwm.timer_index,
            6,
        )

    def test_constructs_from_integer_channel(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                18,
                bus=bus,
            )

        self.assertEqual(
            pwm.channel,
            18,
        )
        self.assertEqual(
            pwm.timer_index,
            5,
        )

    def test_rejects_boolean_channel(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "channel must be",
        ):
            PWM(
                True,
                bus=MagicMock(),
            )

    def test_rejects_invalid_channel_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "channel must be",
        ):
            PWM(  # type: ignore[arg-type]
                object(),
                bus=MagicMock(),
            )

    def test_rejects_unknown_string_channel(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            PWMError,
            "Unknown PWM channel",
        ):
            PWM(
                "P99",
                bus=MagicMock(),
            )

    def test_rejects_out_of_range_integer_channel(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            PWMError,
            "range 0-19",
        ):
            PWM(
                20,
                bus=MagicMock(),
            )

    def test_timer_mapping(
        self,
    ) -> None:
        expected = {
            0: 0,
            3: 0,
            4: 1,
            7: 1,
            8: 2,
            11: 2,
            12: 3,
            15: 3,
            16: 4,
            17: 4,
            18: 5,
            19: 6,
        }

        for channel, timer_index in expected.items():
            with self.subTest(
                channel=channel,
            ):
                self.assertEqual(
                    PWM._timer_index_for_channel(channel),
                    timer_index,
                )

    def test_timer_mapping_rejects_invalid_channel(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            PWMError,
            "Invalid PWM channel",
        ):
            PWM._timer_index_for_channel(20)

    def test_default_constructor_creates_owned_i2c_bus(
        self,
    ) -> None:
        bus = MagicMock()

        with (
            patch(
                "betabox_robotics.hardware.pwm.I2C",
                return_value=bus,
            ) as i2c_type,
            patch.object(
                PWM,
                "set_frequency",
            ),
        ):
            pwm = PWM(
                Pins.P0,
            )

        i2c_type.assert_called_once_with(address=PWM.ADDRESSES)

        self.assertTrue(
            pwm._owns_i2c,
        )
        self.assertIs(
            pwm._bus(),
            bus,
        )

    def test_custom_address_is_forwarded_to_i2c(
        self,
    ) -> None:
        bus = MagicMock()

        with (
            patch(
                "betabox_robotics.hardware.pwm.I2C",
                return_value=bus,
            ) as i2c_type,
            patch.object(
                PWM,
                "set_frequency",
            ),
        ):
            PWM(
                Pins.P0,
                address=0x16,
            )

        i2c_type.assert_called_once_with(address=0x16)

    def test_constructor_uses_borrowed_bus(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        self.assertFalse(
            pwm._owns_i2c,
        )
        self.assertIs(
            pwm._bus(),
            bus,
        )

    def test_constructor_closes_owned_bus_when_initialization_fails(
        self,
    ) -> None:
        bus = MagicMock()

        with (
            patch(
                "betabox_robotics.hardware.pwm.I2C",
                return_value=bus,
            ),
            patch.object(
                PWM,
                "set_frequency",
                side_effect=PWMError("frequency setup failed"),
            ),
            self.assertRaisesRegex(
                PWMError,
                "frequency setup failed",
            ),
        ):
            PWM(
                Pins.P0,
            )

        bus.close.assert_called_once_with()

    def test_constructor_does_not_close_borrowed_bus_when_initialization_fails(
        self,
    ) -> None:
        bus = MagicMock()

        with (
            patch.object(
                PWM,
                "set_frequency",
                side_effect=PWMError("frequency setup failed"),
            ),
            self.assertRaisesRegex(
                PWMError,
                "frequency setup failed",
            ),
        ):
            PWM(
                Pins.P0,
                bus=bus,
            )

        bus.close.assert_not_called()

    def test_write_register_16_writes_register_and_bytes(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        pwm._write_register_16(
            0x40,
            0x1234,
        )

        bus.write.assert_called_once_with(
            [
                0x40,
                0x12,
                0x34,
            ]
        )

    def test_bus_accessor_rejects_closed_pwm(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        pwm.close()

        with self.assertRaisesRegex(
            PWMError,
            "I2C bus is closed",
        ):
            pwm._bus()

    def test_require_finite_number_accepts_int_and_float(
        self,
    ) -> None:
        self.assertEqual(
            PWM._require_finite_number(
                5,
                name="value",
            ),
            5.0,
        )

        self.assertEqual(
            PWM._require_finite_number(
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
            PWM._require_finite_number(
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
            PWM._require_finite_number(
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
            PWM._require_finite_number(
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
            PWM._require_finite_number(
                math.inf,
                name="value",
            )

    def test_set_frequency_programs_selected_prescaler_and_period(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        with (
            patch.object(
                pwm,
                "set_prescaler",
            ) as set_prescaler,
            patch.object(
                pwm,
                "set_period",
            ) as set_period,
        ):
            pwm.set_frequency(50)

        set_prescaler.assert_called_once()
        set_period.assert_called_once()

        selected_prescaler = set_prescaler.call_args.args[0]

        selected_period = set_period.call_args.args[0]

        actual_frequency = PWM.CLOCK / selected_prescaler / selected_period

        self.assertAlmostEqual(
            actual_frequency,
            50,
            places=3,
        )

    def test_set_frequency_rejects_zero(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        with self.assertRaisesRegex(
            PWMError,
            "greater than 0",
        ):
            pwm.set_frequency(0)

    def test_set_frequency_rejects_boolean(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        with self.assertRaisesRegex(
            TypeError,
            "frequency must be a number",
        ):
            pwm.set_frequency(True)

    def test_set_prescaler_updates_state_and_register(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        TIMER_STATE[0]["period"] = 1000

        with patch.object(
            pwm,
            "_write_register_16",
        ) as write_register:
            pwm.set_prescaler(100)

        self.assertEqual(
            pwm.get_prescaler(),
            100,
        )

        self.assertEqual(
            pwm.get_frequency(),
            PWM.CLOCK / 100 / 1000,
        )

        write_register.assert_called_once_with(
            PWM.REG_PSC,
            99,
        )

    def test_set_prescaler_uses_secondary_register_range(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P18,
                bus=bus,
            )

        with patch.object(
            pwm,
            "_write_register_16",
        ) as write_register:
            pwm.set_prescaler(100)

        write_register.assert_called_once_with(
            PWM.REG_PSC2 + 1,
            99,
        )

    def test_set_prescaler_rejects_non_positive_value(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        with self.assertRaisesRegex(
            PWMError,
            "greater than 0",
        ):
            pwm.set_prescaler(0)

    def test_set_period_updates_shared_timer_state(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        pwm._prescaler = 100

        with patch.object(
            pwm,
            "_write_register_16",
        ) as write_register:
            pwm.set_period(1000)

        self.assertEqual(
            pwm.get_period(),
            1000,
        )

        self.assertEqual(
            pwm.get_frequency(),
            PWM.CLOCK / 100 / 1000,
        )

        write_register.assert_called_once_with(
            PWM.REG_ARR,
            1000,
        )

    def test_channels_on_same_timer_share_period(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            first = PWM(
                Pins.P0,
                bus=bus,
            )
            second = PWM(
                Pins.P3,
                bus=bus,
            )

        with patch.object(
            first,
            "_write_register_16",
        ):
            first.set_period(1234)

        self.assertEqual(
            second.get_period(),
            1234,
        )

    def test_set_period_uses_secondary_register_range(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P19,
                bus=bus,
            )

        with patch.object(
            pwm,
            "_write_register_16",
        ) as write_register:
            pwm.set_period(1000)

        write_register.assert_called_once_with(
            PWM.REG_ARR2 + 2,
            1000,
        )

    def test_set_period_rejects_non_positive_value(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        with self.assertRaisesRegex(
            PWMError,
            "greater than 0",
        ):
            pwm.set_period(0)

    def test_set_pulse_width_updates_state_and_register(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P2,
                bus=bus,
            )

        TIMER_STATE[0]["period"] = 1000

        with patch.object(
            pwm,
            "_write_register_16",
        ) as write_register:
            pwm.set_pulse_width(250)

        self.assertEqual(
            pwm.get_pulse_width(),
            250,
        )

        self.assertEqual(
            pwm.get_duty_cycle(),
            25.0,
        )

        write_register.assert_called_once_with(
            PWM.REG_CHN + 2,
            250,
        )

    def test_set_pulse_width_truncates_fractional_value(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        TIMER_STATE[0]["period"] = 1000

        with patch.object(
            pwm,
            "_write_register_16",
        ):
            pwm.set_pulse_width(250.9)

        self.assertEqual(
            pwm.get_pulse_width(),
            250,
        )

    def test_set_pulse_width_rejects_negative_value(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        with self.assertRaisesRegex(
            PWMError,
            "greater than or equal to 0",
        ):
            pwm.set_pulse_width(-1)

    def test_set_pulse_width_rejects_value_above_period(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        TIMER_STATE[0]["period"] = 100

        with self.assertRaisesRegex(
            PWMError,
            "greater than period",
        ):
            pwm.set_pulse_width(101)

    def test_set_duty_cycle_updates_actual_duty_cycle(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        TIMER_STATE[0]["period"] = 1000

        with patch.object(
            pwm,
            "_write_register_16",
        ):
            pwm.set_duty_cycle(25)

        self.assertEqual(
            pwm.get_pulse_width(),
            250,
        )

        self.assertEqual(
            pwm.get_duty_cycle(),
            25.0,
        )

    def test_set_duty_cycle_rejects_out_of_range_values(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        for value in (
            -1,
            101,
        ):
            with (
                self.subTest(
                    value=value,
                ),
                self.assertRaisesRegex(
                    PWMError,
                    "between 0 and 100",
                ),
            ):
                pwm.set_duty_cycle(value)

    def test_off_sets_zero_duty_cycle(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        with patch.object(
            pwm,
            "set_duty_cycle",
        ) as set_duty_cycle:
            pwm.off()

        set_duty_cycle.assert_called_once_with(0)

    def test_compatibility_aliases_get_values(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        pwm._frequency = 50.0
        pwm._prescaler = 100
        pwm._pulse_width = 250
        pwm._duty_cycle = 25.0
        TIMER_STATE[0]["period"] = 1000

        self.assertEqual(
            pwm.freq(),
            50.0,
        )
        self.assertEqual(
            pwm.prescaler(),
            100,
        )
        self.assertEqual(
            pwm.period(),
            1000,
        )
        self.assertEqual(
            pwm.pulse_width(),
            250,
        )
        self.assertEqual(
            pwm.pulse_width_percent(),
            25.0,
        )

    def test_compatibility_aliases_set_values(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        with (
            patch.object(
                pwm,
                "set_frequency",
            ) as set_frequency,
            patch.object(
                pwm,
                "set_prescaler",
            ) as set_prescaler,
            patch.object(
                pwm,
                "set_period",
            ) as set_period,
            patch.object(
                pwm,
                "set_pulse_width",
            ) as set_pulse_width,
            patch.object(
                pwm,
                "set_duty_cycle",
            ) as set_duty_cycle,
        ):
            self.assertIsNone(pwm.freq(60))
            self.assertIsNone(pwm.prescaler(100))
            self.assertIsNone(pwm.period(1000))
            self.assertIsNone(pwm.pulse_width(250))
            self.assertIsNone(pwm.pulse_width_percent(25))

        set_frequency.assert_called_once_with(60)
        set_prescaler.assert_called_once_with(100)
        set_period.assert_called_once_with(1000)
        set_pulse_width.assert_called_once_with(250)
        set_duty_cycle.assert_called_once_with(25)

    def test_close_closes_owned_bus(
        self,
    ) -> None:
        bus = MagicMock()

        with (
            patch(
                "betabox_robotics.hardware.pwm.I2C",
                return_value=bus,
            ),
            patch.object(
                PWM,
                "set_frequency",
            ),
        ):
            pwm = PWM(
                Pins.P0,
            )

        pwm.close()

        bus.close.assert_called_once_with()
        self.assertTrue(
            pwm.closed,
        )

    def test_close_does_not_close_borrowed_bus(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        pwm.close()

        bus.close.assert_not_called()
        self.assertTrue(
            pwm.closed,
        )

    def test_close_is_idempotent(
        self,
    ) -> None:
        bus = MagicMock()

        with (
            patch(
                "betabox_robotics.hardware.pwm.I2C",
                return_value=bus,
            ),
            patch.object(
                PWM,
                "set_frequency",
            ),
        ):
            pwm = PWM(
                Pins.P0,
            )

        pwm.close()
        pwm.close()

        bus.close.assert_called_once_with()

    def test_close_clears_state_when_owned_bus_close_fails(
        self,
    ) -> None:
        bus = MagicMock()
        bus.close.side_effect = OSError("close failed")

        with (
            patch(
                "betabox_robotics.hardware.pwm.I2C",
                return_value=bus,
            ),
            patch.object(
                PWM,
                "set_frequency",
            ),
        ):
            pwm = PWM(
                Pins.P0,
            )

        with self.assertRaisesRegex(
            OSError,
            "close failed",
        ):
            pwm.close()

        self.assertTrue(
            pwm.closed,
        )

    def test_deinit_delegates_to_close(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        pwm.deinit()

        self.assertTrue(
            pwm.closed,
        )

    def test_context_manager_returns_self_and_closes(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

            with pwm as entered:
                self.assertIs(
                    entered,
                    pwm,
                )
                self.assertFalse(
                    pwm.closed,
                )

        self.assertTrue(
            pwm.closed,
        )
        bus.close.assert_not_called()

    def test_closed_pwm_cannot_reenter_context(
        self,
    ) -> None:
        bus = MagicMock()

        with patch.object(
            PWM,
            "set_frequency",
        ):
            pwm = PWM(
                Pins.P0,
                bus=bus,
            )

        pwm.close()

        with (
            self.assertRaisesRegex(
                PWMError,
                "closed PWM",
            ),
            pwm,
        ):
            pass


if __name__ == "__main__":
    unittest.main()
