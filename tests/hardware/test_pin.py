from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from betabox_robotics.hardware.board import (
    DigitalPin,
    Pins,
)
from betabox_robotics.hardware.exceptions import (
    InvalidModeError,
    InvalidPinError,
    PinModeError,
)
from betabox_robotics.hardware.pin import (
    Pin,
    PinMode,
    Pull,
)


class PinTests(unittest.TestCase):
    def test_constructs_output_from_digital_pin(
        self,
    ) -> None:
        output_device = MagicMock()

        with patch(
            "betabox_robotics.hardware.pin.OutputDevice",
            return_value=output_device,
        ) as output_type:
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        output_type.assert_called_once_with(17)

        self.assertEqual(
            pin.pin_number,
            17,
        )
        self.assertEqual(
            pin.board_name,
            "D0",
        )
        self.assertIs(
            pin.mode,
            PinMode.OUT,
        )
        self.assertIs(
            pin.pull,
            Pull.NONE,
        )
        self.assertFalse(
            pin.closed,
        )
        self.assertIs(
            pin.device,
            output_device,
        )

    def test_constructs_output_from_string_name(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.pin.OutputDevice"):
            pin = Pin(
                "D7",
                mode=Pin.OUT,
            )

        self.assertEqual(
            pin.pin_number,
            4,
        )
        self.assertEqual(
            pin.board_name,
            "D7",
        )

    def test_constructs_output_from_gpio_number(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.pin.OutputDevice"):
            pin = Pin(
                17,
                mode=Pin.OUT,
            )

        self.assertEqual(
            pin.pin_number,
            17,
        )
        self.assertIsNone(
            pin.board_name,
        )

    def test_digital_pin_alias_uses_canonical_enum_name(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.pin.OutputDevice"):
            pin = Pin(
                DigitalPin.D7,
                mode=Pin.OUT,
            )

        self.assertEqual(
            pin.pin_number,
            4,
        )

        # D7 is an IntEnum alias of D1.
        self.assertEqual(
            pin.board_name,
            "D1",
        )

    def test_unknown_string_pin_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            InvalidPinError,
            "Unknown pin name",
        ):
            Pin(
                "D99",
                mode=Pin.OUT,
            )

    def test_unknown_gpio_number_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            InvalidPinError,
            "Unknown GPIO pin",
        ):
            Pin(
                999,
                mode=Pin.OUT,
            )

    def test_invalid_pin_type_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            InvalidPinError,
            "pin must be",
        ):
            Pin(  # type: ignore[arg-type]
                object(),
                mode=Pin.OUT,
            )

    def test_invalid_mode_type_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "mode must be",
        ):
            Pin(  # type: ignore[arg-type]
                Pins.D0,
                mode="out",
            )

    def test_invalid_pull_type_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "pull must be",
        ):
            Pin(  # type: ignore[arg-type]
                Pins.D0,
                mode=Pin.IN,
                pull="down",
            )

    def test_pull_up_input_configuration(
        self,
    ) -> None:
        input_device = MagicMock()

        with patch(
            "betabox_robotics.hardware.pin.InputDevice",
            return_value=input_device,
        ) as input_type:
            pin = Pin(
                Pins.D0,
                mode=Pin.IN,
                pull=Pin.PULL_UP,
            )

        input_type.assert_called_once_with(
            17,
            pull_up=True,
            active_state=None,
        )

        self.assertIs(
            pin.mode,
            PinMode.IN,
        )
        self.assertIs(
            pin.pull,
            Pull.UP,
        )
        self.assertIsNone(
            pin.active_state,
        )

    def test_pull_down_input_configuration(
        self,
    ) -> None:
        input_device = MagicMock()

        with patch(
            "betabox_robotics.hardware.pin.InputDevice",
            return_value=input_device,
        ) as input_type:
            pin = Pin(
                Pins.D0,
                mode=Pin.IN,
                pull=Pin.PULL_DOWN,
            )

        input_type.assert_called_once_with(
            17,
            pull_up=False,
            active_state=None,
        )

        self.assertIs(
            pin.pull,
            Pull.DOWN,
        )

    def test_floating_input_requires_active_state(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            InvalidModeError,
            "active_state is required",
        ):
            Pin(
                Pins.D0,
                mode=Pin.IN,
                pull=Pin.PULL_NONE,
            )

    def test_floating_input_uses_no_internal_pull(
        self,
    ) -> None:
        input_device = MagicMock()

        with patch(
            "betabox_robotics.hardware.pin.InputDevice",
            return_value=input_device,
        ) as input_type:
            pin = Pin(
                Pins.D0,
                mode=Pin.IN,
                pull=Pin.PULL_NONE,
                active_state=True,
            )

        input_type.assert_called_once_with(
            17,
            pull_up=None,
            active_state=True,
        )

        self.assertIs(
            pin.pull,
            Pull.NONE,
        )
        self.assertTrue(
            pin.active_state,
        )

    def test_output_ignores_pull_configuration(
        self,
    ) -> None:
        output_device = MagicMock()

        with patch(
            "betabox_robotics.hardware.pin.OutputDevice",
            return_value=output_device,
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
                pull=Pin.PULL_UP,
            )

        self.assertIs(
            pin.mode,
            PinMode.OUT,
        )
        self.assertIs(
            pin.pull,
            Pull.UP,
        )

    def test_switching_mode_closes_previous_device(
        self,
    ) -> None:
        output_device = MagicMock()
        input_device = MagicMock()

        with (
            patch(
                "betabox_robotics.hardware.pin.OutputDevice",
                return_value=output_device,
            ),
            patch(
                "betabox_robotics.hardware.pin.InputDevice",
                return_value=input_device,
            ),
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

            pin.input(
                pull=Pin.PULL_DOWN,
            )

        output_device.close.assert_called_once_with()

        self.assertIs(
            pin.device,
            input_device,
        )
        self.assertIs(
            pin.mode,
            PinMode.IN,
        )
        self.assertIs(
            pin.pull,
            Pull.DOWN,
        )

    def test_output_switch_closes_previous_input(
        self,
    ) -> None:
        input_device = MagicMock()
        output_device = MagicMock()

        with (
            patch(
                "betabox_robotics.hardware.pin.InputDevice",
                return_value=input_device,
            ),
            patch(
                "betabox_robotics.hardware.pin.OutputDevice",
                return_value=output_device,
            ),
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.IN,
                pull=Pin.PULL_DOWN,
            )

            pin.output()

        input_device.close.assert_called_once_with()

        self.assertIs(
            pin.device,
            output_device,
        )
        self.assertIs(
            pin.mode,
            PinMode.OUT,
        )

    def test_read_returns_integer_value(
        self,
    ) -> None:
        input_device = MagicMock()
        input_device.value = True

        with patch(
            "betabox_robotics.hardware.pin.InputDevice",
            return_value=input_device,
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.IN,
                pull=Pin.PULL_DOWN,
            )

        self.assertEqual(
            pin.read(),
            1,
        )

        input_device.value = False

        self.assertEqual(
            pin.read(),
            0,
        )

    def test_read_requires_input_mode(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.pin.OutputDevice"):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        with self.assertRaisesRegex(
            PinModeError,
            "not configured as input",
        ):
            pin.read()

    def test_write_high_turns_output_on(
        self,
    ) -> None:
        output_device = MagicMock()

        with patch(
            "betabox_robotics.hardware.pin.OutputDevice",
            return_value=output_device,
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        self.assertEqual(
            pin.write(True),
            1,
        )

        output_device.on.assert_called_once_with()
        output_device.off.assert_not_called()

    def test_write_low_turns_output_off(
        self,
    ) -> None:
        output_device = MagicMock()

        with patch(
            "betabox_robotics.hardware.pin.OutputDevice",
            return_value=output_device,
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        self.assertEqual(
            pin.write(False),
            0,
        )

        output_device.off.assert_called_once_with()
        output_device.on.assert_not_called()

    def test_write_uses_truthiness(
        self,
    ) -> None:
        output_device = MagicMock()

        with patch(
            "betabox_robotics.hardware.pin.OutputDevice",
            return_value=output_device,
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        self.assertEqual(
            pin.write(1),  # type: ignore[arg-type]
            1,
        )

        output_device.on.assert_called_once_with()

    def test_write_requires_output_mode(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.pin.InputDevice"):
            pin = Pin(
                Pins.D0,
                mode=Pin.IN,
                pull=Pin.PULL_DOWN,
            )

        with self.assertRaisesRegex(
            PinModeError,
            "not configured as output",
        ):
            pin.write(True)

    def test_on_off_high_and_low_delegate_to_write(
        self,
    ) -> None:
        output_device = MagicMock()

        with patch(
            "betabox_robotics.hardware.pin.OutputDevice",
            return_value=output_device,
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        self.assertEqual(
            pin.on(),
            1,
        )
        self.assertEqual(
            pin.off(),
            0,
        )
        self.assertEqual(
            pin.high(),
            1,
        )
        self.assertEqual(
            pin.low(),
            0,
        )

        self.assertEqual(
            output_device.on.call_count,
            2,
        )
        self.assertEqual(
            output_device.off.call_count,
            2,
        )

    def test_toggle_turns_off_active_output(
        self,
    ) -> None:
        output_device = MagicMock()
        output_device.value = True

        with patch(
            "betabox_robotics.hardware.pin.OutputDevice",
            return_value=output_device,
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        self.assertEqual(
            pin.toggle(),
            0,
        )

        output_device.off.assert_called_once_with()

    def test_toggle_turns_on_inactive_output(
        self,
    ) -> None:
        output_device = MagicMock()
        output_device.value = False

        with patch(
            "betabox_robotics.hardware.pin.OutputDevice",
            return_value=output_device,
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        self.assertEqual(
            pin.toggle(),
            1,
        )

        output_device.on.assert_called_once_with()

    def test_toggle_requires_output_mode(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.pin.InputDevice"):
            pin = Pin(
                Pins.D0,
                mode=Pin.IN,
                pull=Pin.PULL_DOWN,
            )

        with self.assertRaisesRegex(
            PinModeError,
            "not configured as output",
        ):
            pin.toggle()

    def test_value_reads_when_no_value_is_given(
        self,
    ) -> None:
        input_device = MagicMock()
        input_device.value = True

        with patch(
            "betabox_robotics.hardware.pin.InputDevice",
            return_value=input_device,
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.IN,
                pull=Pin.PULL_DOWN,
            )

        self.assertEqual(
            pin.value(),
            1,
        )
        self.assertEqual(
            pin(),
            1,
        )

    def test_value_writes_when_value_is_given(
        self,
    ) -> None:
        output_device = MagicMock()

        with patch(
            "betabox_robotics.hardware.pin.OutputDevice",
            return_value=output_device,
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        self.assertEqual(
            pin.value(True),
            1,
        )
        self.assertEqual(
            pin(False),
            0,
        )

        output_device.on.assert_called_once_with()
        output_device.off.assert_called_once_with()

    def test_name_returns_gpio_name(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.pin.OutputDevice"):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        self.assertEqual(
            pin.name(),
            "GPIO17",
        )

    def test_irq_requires_callable_handler(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.pin.OutputDevice"):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        with self.assertRaisesRegex(
            TypeError,
            "handler must be callable",
        ):
            pin.irq(  # type: ignore[arg-type]
                "handler",
            )

    def test_irq_rejects_invalid_trigger_type(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.pin.OutputDevice"):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        with self.assertRaisesRegex(
            TypeError,
            "trigger must be",
        ):
            pin.irq(  # type: ignore[arg-type]
                MagicMock(),
                trigger="falling",
            )

    def test_irq_rejects_invalid_pull_type(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.pin.OutputDevice"):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        with self.assertRaisesRegex(
            TypeError,
            "pull must be",
        ):
            pin.irq(  # type: ignore[arg-type]
                MagicMock(),
                pull="up",
            )

    def test_irq_rejects_no_pull(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.pin.OutputDevice"):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        with self.assertRaisesRegex(
            InvalidModeError,
            "interrupt pins require",
        ):
            pin.irq(
                MagicMock(),
                pull=Pin.PULL_NONE,
            )

    def test_irq_rejects_boolean_bouncetime(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.pin.OutputDevice"):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        with self.assertRaisesRegex(
            TypeError,
            "bouncetime must be an integer",
        ):
            pin.irq(
                MagicMock(),
                bouncetime=True,
            )

    def test_irq_rejects_non_integer_bouncetime(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.pin.OutputDevice"):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        with self.assertRaisesRegex(
            TypeError,
            "bouncetime must be an integer",
        ):
            pin.irq(  # type: ignore[arg-type]
                MagicMock(),
                bouncetime=12.5,
            )

    def test_irq_rejects_negative_bouncetime(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.pin.OutputDevice"):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        with self.assertRaisesRegex(
            ValueError,
            "bouncetime cannot be negative",
        ):
            pin.irq(
                MagicMock(),
                bouncetime=-1,
            )

    def test_irq_falling_with_pull_up_uses_when_pressed(
        self,
    ) -> None:
        output_device = MagicMock()
        button = MagicMock()
        handler = MagicMock()

        with (
            patch(
                "betabox_robotics.hardware.pin.OutputDevice",
                return_value=output_device,
            ),
            patch(
                "betabox_robotics.hardware.pin.Button",
                return_value=button,
            ) as button_type,
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

            pin.irq(
                handler,
                trigger=Pin.IRQ_FALLING,
                bouncetime=250,
                pull=Pin.PULL_UP,
            )

        output_device.close.assert_called_once_with()

        button_type.assert_called_once_with(
            pin=17,
            pull_up=True,
            bounce_time=0.25,
        )

        self.assertIs(
            button.when_pressed,
            handler,
        )

        self.assertIs(
            pin.mode,
            PinMode.IN,
        )
        self.assertIs(
            pin.pull,
            Pull.UP,
        )
        self.assertEqual(
            pin.bounce_time,
            0.25,
        )

    def test_irq_rising_with_pull_up_uses_when_released(
        self,
    ) -> None:
        button = MagicMock()
        handler = MagicMock()

        with (
            patch("betabox_robotics.hardware.pin.OutputDevice"),
            patch(
                "betabox_robotics.hardware.pin.Button",
                return_value=button,
            ),
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

            pin.irq(
                handler,
                trigger=Pin.IRQ_RISING,
                pull=Pin.PULL_UP,
            )

        self.assertIs(
            button.when_released,
            handler,
        )

    def test_irq_falling_with_pull_down_uses_when_released(
        self,
    ) -> None:
        button = MagicMock()
        handler = MagicMock()

        with (
            patch("betabox_robotics.hardware.pin.OutputDevice"),
            patch(
                "betabox_robotics.hardware.pin.Button",
                return_value=button,
            ),
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

            pin.irq(
                handler,
                trigger=Pin.IRQ_FALLING,
                pull=Pin.PULL_DOWN,
            )

        self.assertIs(
            button.when_released,
            handler,
        )

    def test_irq_rising_with_pull_down_uses_when_pressed(
        self,
    ) -> None:
        button = MagicMock()
        handler = MagicMock()

        with (
            patch("betabox_robotics.hardware.pin.OutputDevice"),
            patch(
                "betabox_robotics.hardware.pin.Button",
                return_value=button,
            ),
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

            pin.irq(
                handler,
                trigger=Pin.IRQ_RISING,
                pull=Pin.PULL_DOWN,
            )

        self.assertIs(
            button.when_pressed,
            handler,
        )

    def test_irq_both_sets_both_callbacks(
        self,
    ) -> None:
        button = MagicMock()
        handler = MagicMock()

        with (
            patch("betabox_robotics.hardware.pin.OutputDevice"),
            patch(
                "betabox_robotics.hardware.pin.Button",
                return_value=button,
            ),
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

            pin.irq(
                handler,
                trigger=Pin.IRQ_BOTH,
                pull=Pin.PULL_UP,
            )

        self.assertIs(
            button.when_pressed,
            handler,
        )
        self.assertIs(
            button.when_released,
            handler,
        )

    def test_close_closes_device_and_clears_state(
        self,
    ) -> None:
        output_device = MagicMock()

        with patch(
            "betabox_robotics.hardware.pin.OutputDevice",
            return_value=output_device,
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        pin.close()

        output_device.close.assert_called_once_with()

        self.assertTrue(
            pin.closed,
        )
        self.assertIsNone(
            pin.mode,
        )
        self.assertIsNone(
            pin.pull,
        )
        self.assertIsNone(
            pin.active_state,
        )
        self.assertIsNone(
            pin.bounce_time,
        )

    def test_close_is_idempotent(
        self,
    ) -> None:
        output_device = MagicMock()

        with patch(
            "betabox_robotics.hardware.pin.OutputDevice",
            return_value=output_device,
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        pin.close()
        pin.close()

        output_device.close.assert_called_once_with()

    def test_close_clears_state_when_device_close_fails(
        self,
    ) -> None:
        output_device = MagicMock()
        output_device.close.side_effect = RuntimeError("close failed")

        with patch(
            "betabox_robotics.hardware.pin.OutputDevice",
            return_value=output_device,
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        with self.assertRaisesRegex(
            RuntimeError,
            "close failed",
        ):
            pin.close()

        self.assertTrue(
            pin.closed,
        )
        self.assertIsNone(
            pin.mode,
        )
        self.assertIsNone(
            pin.pull,
        )

    def test_device_property_rejects_closed_pin(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.pin.OutputDevice"):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        pin.close()

        with self.assertRaisesRegex(
            RuntimeError,
            "closed",
        ):
            _ = pin.device

    def test_context_manager_returns_self_and_closes(
        self,
    ) -> None:
        output_device = MagicMock()

        with patch(
            "betabox_robotics.hardware.pin.OutputDevice",
            return_value=output_device,
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

            with pin as entered:
                self.assertIs(
                    entered,
                    pin,
                )
                self.assertFalse(
                    pin.closed,
                )

        output_device.close.assert_called_once_with()
        self.assertTrue(
            pin.closed,
        )

    def test_closed_pin_cannot_reenter_context(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.pin.OutputDevice"):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        pin.close()

        with (
            self.assertRaisesRegex(
                RuntimeError,
                "closed Pin",
            ),
            pin,
        ):
            pass

    def test_deinit_delegates_to_close(
        self,
    ) -> None:
        output_device = MagicMock()

        with patch(
            "betabox_robotics.hardware.pin.OutputDevice",
            return_value=output_device,
        ):
            pin = Pin(
                Pins.D0,
                mode=Pin.OUT,
            )

        pin.deinit()

        output_device.close.assert_called_once_with()
        self.assertTrue(
            pin.closed,
        )


if __name__ == "__main__":
    unittest.main()
