from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from betabox_robotics.hardware.adc import (
    ADC,
    ADCError,
)
from betabox_robotics.hardware.board import (
    AnalogChannel,
    Pins,
)


class ADCTests(unittest.TestCase):
    def test_constructs_from_analog_channel(
        self,
    ) -> None:
        bus = MagicMock()

        adc = ADC(
            AnalogChannel.A0,
            bus=bus,
        )

        self.assertEqual(
            adc.channel,
            0,
        )
        self.assertEqual(
            adc.register,
            0x17,
        )
        self.assertIs(
            adc._bus(),
            bus,
        )
        self.assertFalse(
            adc.closed,
        )

    def test_constructs_from_string_channel(
        self,
    ) -> None:
        adc = ADC(
            "A7",
            bus=MagicMock(),
        )

        self.assertEqual(
            adc.channel,
            7,
        )
        self.assertEqual(
            adc.register,
            0x10,
        )

    def test_constructs_from_integer_channel(
        self,
    ) -> None:
        adc = ADC(
            3,
            bus=MagicMock(),
        )

        self.assertEqual(
            adc.channel,
            3,
        )
        self.assertEqual(
            adc.register,
            0x14,
        )

    def test_rejects_boolean_channel(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "channel must be",
        ):
            ADC(
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
            ADC(  # type: ignore[arg-type]
                object(),
                bus=MagicMock(),
            )

    def test_rejects_unknown_string_channel(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ADCError,
            "Unknown ADC channel",
        ):
            ADC(
                "A99",
                bus=MagicMock(),
            )

    def test_rejects_out_of_range_integer_channel(
        self,
    ) -> None:
        for channel in (
            -1,
            8,
        ):
            with (
                self.subTest(
                    channel=channel,
                ),
                self.assertRaisesRegex(
                    ADCError,
                    "range 0-7",
                ),
            ):
                ADC(
                    channel,
                    bus=MagicMock(),
                )

    def test_channel_register_mapping(
        self,
    ) -> None:
        expected = {
            0: 0x17,
            1: 0x16,
            2: 0x15,
            3: 0x14,
            4: 0x13,
            5: 0x12,
            6: 0x11,
            7: 0x10,
        }

        for channel, register in expected.items():
            with self.subTest(
                channel=channel,
            ):
                self.assertEqual(
                    ADC._channel_to_register(channel),
                    register,
                )

    def test_channel_register_mapping_rejects_boolean(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "channel must be an integer",
        ):
            ADC._channel_to_register(True)

    def test_channel_register_mapping_rejects_invalid_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "channel must be an integer",
        ):
            ADC._channel_to_register(  # type: ignore[arg-type]
                "0"
            )

    def test_channel_register_mapping_rejects_out_of_range_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ADCError,
            "range 0-7",
        ):
            ADC._channel_to_register(8)

    def test_default_constructor_creates_owned_i2c_bus(
        self,
    ) -> None:
        bus = MagicMock()

        with patch(
            "betabox_robotics.hardware.adc.I2C",
            return_value=bus,
        ) as i2c_type:
            adc = ADC(
                Pins.A0,
            )

        i2c_type.assert_called_once_with(address=ADC.ADDRESSES)

        self.assertTrue(
            adc._owns_i2c,
        )
        self.assertIs(
            adc._bus(),
            bus,
        )

    def test_custom_address_is_forwarded_to_i2c(
        self,
    ) -> None:
        bus = MagicMock()

        with patch(
            "betabox_robotics.hardware.adc.I2C",
            return_value=bus,
        ) as i2c_type:
            ADC(
                Pins.A0,
                address=0x15,
            )

        i2c_type.assert_called_once_with(address=0x15)

    def test_address_sequence_is_forwarded_to_i2c(
        self,
    ) -> None:
        bus = MagicMock()
        addresses = (
            0x14,
            0x15,
        )

        with patch(
            "betabox_robotics.hardware.adc.I2C",
            return_value=bus,
        ) as i2c_type:
            ADC(
                Pins.A0,
                address=addresses,
            )

        i2c_type.assert_called_once_with(address=addresses)

    def test_constructor_uses_borrowed_bus(
        self,
    ) -> None:
        bus = MagicMock()

        adc = ADC(
            Pins.A0,
            bus=bus,
        )

        self.assertFalse(
            adc._owns_i2c,
        )
        self.assertIs(
            adc._bus(),
            bus,
        )

    def test_read_writes_register_and_combines_bytes(
        self,
    ) -> None:
        bus = MagicMock()
        bus.read.return_value = [
            0x0A,
            0xBC,
        ]

        adc = ADC(
            Pins.A0,
            bus=bus,
        )

        result = adc.read()

        bus.write.assert_called_once_with(
            [
                0x17,
                0,
                0,
            ]
        )
        bus.read.assert_called_once_with(2)

        self.assertEqual(
            result,
            0x0ABC,
        )

    def test_read_rejects_short_response(
        self,
    ) -> None:
        bus = MagicMock()
        bus.read.return_value = [
            0x12,
        ]

        adc = ADC(
            Pins.A0,
            bus=bus,
        )

        with self.assertRaisesRegex(
            ADCError,
            "unexpected number of bytes",
        ):
            adc.read()

    def test_read_rejects_long_response(
        self,
    ) -> None:
        bus = MagicMock()
        bus.read.return_value = [
            0x01,
            0x02,
            0x03,
        ]

        adc = ADC(
            Pins.A0,
            bus=bus,
        )

        with self.assertRaisesRegex(
            ADCError,
            "unexpected number of bytes",
        ):
            adc.read()

    def test_read_voltage_converts_full_scale(
        self,
    ) -> None:
        adc = ADC(
            Pins.A0,
            bus=MagicMock(),
        )

        with patch.object(
            adc,
            "read",
            return_value=ADC.MAX_VALUE,
        ):
            voltage = adc.read_voltage()

        self.assertAlmostEqual(
            voltage,
            ADC.REFERENCE_VOLTAGE,
        )

    def test_read_voltage_converts_half_scale(
        self,
    ) -> None:
        adc = ADC(
            Pins.A0,
            bus=MagicMock(),
        )

        with patch.object(
            adc,
            "read",
            return_value=ADC.MAX_VALUE / 2,
        ):
            voltage = adc.read_voltage()

        self.assertAlmostEqual(
            voltage,
            ADC.REFERENCE_VOLTAGE / 2,
        )

    def test_bus_accessor_rejects_closed_adc(
        self,
    ) -> None:
        adc = ADC(
            Pins.A0,
            bus=MagicMock(),
        )

        adc.close()

        with self.assertRaisesRegex(
            ADCError,
            "I2C bus is closed",
        ):
            adc._bus()

    def test_close_closes_owned_bus(
        self,
    ) -> None:
        bus = MagicMock()

        with patch(
            "betabox_robotics.hardware.adc.I2C",
            return_value=bus,
        ):
            adc = ADC(
                Pins.A0,
            )

        adc.close()

        bus.close.assert_called_once_with()
        self.assertTrue(
            adc.closed,
        )

    def test_close_does_not_close_borrowed_bus(
        self,
    ) -> None:
        bus = MagicMock()

        adc = ADC(
            Pins.A0,
            bus=bus,
        )

        adc.close()

        bus.close.assert_not_called()
        self.assertTrue(
            adc.closed,
        )

    def test_close_is_idempotent(
        self,
    ) -> None:
        bus = MagicMock()

        with patch(
            "betabox_robotics.hardware.adc.I2C",
            return_value=bus,
        ):
            adc = ADC(
                Pins.A0,
            )

        adc.close()
        adc.close()

        bus.close.assert_called_once_with()

    def test_close_clears_state_when_owned_bus_close_fails(
        self,
    ) -> None:
        bus = MagicMock()
        bus.close.side_effect = OSError("close failed")

        with patch(
            "betabox_robotics.hardware.adc.I2C",
            return_value=bus,
        ):
            adc = ADC(
                Pins.A0,
            )

        with self.assertRaisesRegex(
            OSError,
            "close failed",
        ):
            adc.close()

        self.assertTrue(
            adc.closed,
        )

    def test_deinit_delegates_to_close(
        self,
    ) -> None:
        adc = ADC(
            Pins.A0,
            bus=MagicMock(),
        )

        adc.deinit()

        self.assertTrue(
            adc.closed,
        )

    def test_context_manager_returns_self_and_closes(
        self,
    ) -> None:
        bus = MagicMock()

        adc = ADC(
            Pins.A0,
            bus=bus,
        )

        with adc as entered:
            self.assertIs(
                entered,
                adc,
            )
            self.assertFalse(
                adc.closed,
            )

        self.assertTrue(
            adc.closed,
        )
        bus.close.assert_not_called()

    def test_closed_adc_cannot_reenter_context(
        self,
    ) -> None:
        adc = ADC(
            Pins.A0,
            bus=MagicMock(),
        )

        adc.close()

        with (
            self.assertRaisesRegex(
                ADCError,
                "closed ADC",
            ),
            adc,
        ):
            pass


if __name__ == "__main__":
    unittest.main()
