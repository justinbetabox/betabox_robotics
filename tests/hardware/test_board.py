from __future__ import annotations

import unittest

from betabox_robotics.hardware.board import (
    ADC_CHANNELS,
    BOARD_PINS,
    PWM_CHANNELS,
    AnalogChannel,
    DigitalPin,
    Pins,
    PWMChannel,
)


class BoardMappingTests(unittest.TestCase):
    def test_identifiers_are_integer_compatible(self) -> None:
        self.assertEqual(int(DigitalPin.D0), 17)
        self.assertEqual(int(PWMChannel.P13), 13)
        self.assertEqual(int(AnalogChannel.A7), 7)

    def test_digital_aliases_share_expected_gpio_numbers(self) -> None:
        self.assertIs(DigitalPin.D7, DigitalPin.D1)
        self.assertIs(DigitalPin.SW, DigitalPin.D6)
        self.assertIs(DigitalPin.USER, DigitalPin.D6)

    def test_board_pin_lookup_preserves_alias_names(self) -> None:
        self.assertEqual(BOARD_PINS["D1"], 4)
        self.assertEqual(BOARD_PINS["D7"], 4)
        self.assertEqual(BOARD_PINS["D6"], 25)
        self.assertEqual(BOARD_PINS["SW"], 25)
        self.assertEqual(BOARD_PINS["USER"], 25)

    def test_channel_lookup_tables_are_complete(self) -> None:
        self.assertEqual(len(PWM_CHANNELS), 20)
        self.assertEqual(len(ADC_CHANNELS), 8)

        self.assertEqual(PWM_CHANNELS["P0"], 0)
        self.assertEqual(PWM_CHANNELS["P19"], 19)
        self.assertEqual(ADC_CHANNELS["A0"], 0)
        self.assertEqual(ADC_CHANNELS["A7"], 7)

    def test_pins_namespace_exposes_all_identifier_types(self) -> None:
        self.assertIs(Pins.D0, DigitalPin.D0)
        self.assertIs(Pins.A0, AnalogChannel.A0)
        self.assertIs(Pins.P0, PWMChannel.P0)
        self.assertIs(Pins.USER, DigitalPin.USER)

    def test_pins_namespace_cannot_be_instantiated(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "Pins is a namespace",
        ):
            Pins()


if __name__ == "__main__":
    unittest.main()
