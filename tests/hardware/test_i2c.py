from __future__ import annotations

import subprocess
import unittest
from unittest.mock import MagicMock, patch

from betabox_robotics.hardware.i2c import (
    I2C,
    I2CError,
)


class I2CTests(unittest.TestCase):
    def test_opens_configured_bus(
        self,
    ) -> None:
        smbus = MagicMock()

        with patch(
            "betabox_robotics.hardware.i2c.SMBus",
            return_value=smbus,
        ) as smbus_type:
            i2c = I2C(
                address=0x14,
                bus=3,
                retry_count=4,
            )

        smbus_type.assert_called_once_with(3)

        self.assertEqual(
            i2c.bus_number,
            3,
        )
        self.assertEqual(
            i2c.retry_count,
            4,
        )
        self.assertEqual(
            i2c.address,
            0x14,
        )
        self.assertFalse(
            i2c.closed,
        )

        i2c.close()

    def test_none_address_is_allowed(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C()

        self.assertIsNone(
            i2c.address,
        )

        i2c.close()

    def test_rejects_boolean_bus_number(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.hardware.i2c.SMBus") as smbus_type,
            self.assertRaisesRegex(
                TypeError,
                "bus must be an integer",
            ),
        ):
            I2C(
                bus=True,
            )

        smbus_type.assert_not_called()

    def test_rejects_boolean_write_data(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with self.assertRaisesRegex(
            TypeError,
            "write data must be",
        ):
            i2c._normalize_write_data(True)

        i2c.close()

    def test_rejects_empty_write_list(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with self.assertRaisesRegex(
            ValueError,
            "write data cannot be empty",
        ):
            i2c._normalize_write_data([])

        i2c.close()

    def test_rejects_empty_bytearray(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with self.assertRaisesRegex(
            ValueError,
            "write data cannot be empty",
        ):
            i2c._normalize_write_data(bytearray())

        i2c.close()

    def test_rejects_boolean_list_value(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with self.assertRaisesRegex(
            TypeError,
            "data values must be integers",
        ):
            i2c._normalize_write_data(
                [
                    0x01,
                    True,
                ]
            )

        i2c.close()

    def test_rejects_non_integer_list_value(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with self.assertRaisesRegex(
            TypeError,
            "data values must be integers",
        ):
            i2c._normalize_write_data(
                [
                    0x01,
                    "bad",  # type: ignore[list-item]
                ]
            )

        i2c.close()

    def test_rejects_negative_list_byte(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with self.assertRaisesRegex(
            ValueError,
            "between 0 and 255",
        ):
            i2c._normalize_write_data(
                [
                    0x01,
                    -1,
                ]
            )

        i2c.close()

    def test_rejects_list_byte_above_255(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with self.assertRaisesRegex(
            ValueError,
            "between 0 and 255",
        ):
            i2c._normalize_write_data(
                [
                    0x01,
                    256,
                ]
            )

        i2c.close()

    def test_normalized_list_is_a_copy(
        self,
    ) -> None:
        source = [
            0x01,
            0x02,
        ]

        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        result = i2c._normalize_write_data(source)

        self.assertEqual(
            result,
            source,
        )

        self.assertIsNot(
            result,
            source,
        )

        i2c.close()

    def test_rejects_non_integer_bus_number(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.hardware.i2c.SMBus") as smbus_type,
            self.assertRaisesRegex(
                TypeError,
                "bus must be an integer",
            ),
        ):
            I2C(
                bus="1",  # type: ignore[arg-type]
            )

        smbus_type.assert_not_called()

    def test_rejects_negative_bus_number(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.hardware.i2c.SMBus") as smbus_type,
            self.assertRaisesRegex(
                ValueError,
                "bus cannot be negative",
            ),
        ):
            I2C(
                bus=-1,
            )

        smbus_type.assert_not_called()

    def test_rejects_boolean_retry_count(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.hardware.i2c.SMBus") as smbus_type,
            self.assertRaisesRegex(
                TypeError,
                "retry_count must be an integer",
            ),
        ):
            I2C(
                retry_count=True,
            )

        smbus_type.assert_not_called()

    def test_rejects_non_integer_retry_count(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.hardware.i2c.SMBus") as smbus_type,
            self.assertRaisesRegex(
                TypeError,
                "retry_count must be an integer",
            ),
        ):
            I2C(
                retry_count=2.5,  # type: ignore[arg-type]
            )

        smbus_type.assert_not_called()

    def test_rejects_zero_retry_count(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.hardware.i2c.SMBus") as smbus_type,
            self.assertRaisesRegex(
                ValueError,
                "retry_count must be at least 1",
            ),
        ):
            I2C(
                retry_count=0,
            )

        smbus_type.assert_not_called()

    def test_rejects_boolean_address(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.hardware.i2c.SMBus") as smbus_type,
            self.assertRaisesRegex(
                TypeError,
                "I2C addresses must be integers",
            ),
        ):
            I2C(
                address=True,
            )

        smbus_type.assert_not_called()

    def test_rejects_non_integer_address(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.hardware.i2c.SMBus") as smbus_type,
            self.assertRaisesRegex(
                TypeError,
                "I2C addresses must be integers",
            ),
        ):
            I2C(
                address="0x14",  # type: ignore[arg-type]
            )

        smbus_type.assert_not_called()

    def test_rejects_negative_address(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.hardware.i2c.SMBus") as smbus_type,
            self.assertRaisesRegex(
                ValueError,
                "between 0x00 and 0x7F",
            ),
        ):
            I2C(
                address=-1,
            )

        smbus_type.assert_not_called()

    def test_rejects_address_above_seven_bit_range(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.hardware.i2c.SMBus") as smbus_type,
            self.assertRaisesRegex(
                ValueError,
                "between 0x00 and 0x7F",
            ),
        ):
            I2C(
                address=0x80,
            )

        smbus_type.assert_not_called()

    def test_rejects_empty_address_candidate_list(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.hardware.i2c.SMBus") as smbus_type,
            self.assertRaisesRegex(
                ValueError,
                "address candidate sequence cannot be empty",
            ),
        ):
            I2C(
                address=[],
            )

        smbus_type.assert_not_called()

    def test_rejects_invalid_address_candidate(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.hardware.i2c.SMBus") as smbus_type,
            self.assertRaisesRegex(
                ValueError,
                "between 0x00 and 0x7F",
            ),
        ):
            I2C(
                address=[
                    0x14,
                    0x80,
                ],
            )

        smbus_type.assert_not_called()

    def test_selects_first_connected_candidate(
        self,
    ) -> None:
        smbus = MagicMock()

        with (
            patch(
                "betabox_robotics.hardware.i2c.SMBus",
                return_value=smbus,
            ),
            patch.object(
                I2C,
                "scan",
                return_value=[
                    0x15,
                    0x16,
                ],
            ) as scan,
        ):
            i2c = I2C(
                address=[
                    0x14,
                    0x15,
                    0x16,
                ],
            )

        scan.assert_called_once_with()

        self.assertEqual(
            i2c.address,
            0x15,
        )

        i2c.close()

    def test_list_candidate_sequence_preserves_first_address_fallback(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.hardware.i2c.SMBus"),
            patch.object(
                I2C,
                "scan",
                return_value=[],
            ),
        ):
            i2c = I2C(
                address=[
                    0x14,
                    0x15,
                ],
            )

        self.assertEqual(
            i2c.address,
            0x14,
        )

        i2c.close()

    def test_constructor_closes_bus_when_address_selection_fails(
        self,
    ) -> None:
        smbus = MagicMock()

        with (
            patch(
                "betabox_robotics.hardware.i2c.SMBus",
                return_value=smbus,
            ),
            patch.object(
                I2C,
                "scan",
                side_effect=I2CError("scan failed"),
            ),
            self.assertRaisesRegex(
                I2CError,
                "scan failed",
            ),
        ):
            I2C(
                address=[
                    0x14,
                    0x15,
                ],
            )

        smbus.close.assert_called_once_with()

    def test_close_closes_bus_and_clears_state(
        self,
    ) -> None:
        smbus = MagicMock()

        with patch(
            "betabox_robotics.hardware.i2c.SMBus",
            return_value=smbus,
        ):
            i2c = I2C(
                address=0x14,
            )

        i2c.close()

        smbus.close.assert_called_once_with()

        self.assertTrue(
            i2c.closed,
        )

    def test_close_is_idempotent(
        self,
    ) -> None:
        smbus = MagicMock()

        with patch(
            "betabox_robotics.hardware.i2c.SMBus",
            return_value=smbus,
        ):
            i2c = I2C(
                address=0x14,
            )

        i2c.close()
        i2c.close()

        smbus.close.assert_called_once_with()

    def test_close_clears_state_when_backend_close_fails(
        self,
    ) -> None:
        smbus = MagicMock()
        smbus.close.side_effect = OSError("close failed")

        with patch(
            "betabox_robotics.hardware.i2c.SMBus",
            return_value=smbus,
        ):
            i2c = I2C(
                address=0x14,
            )

        with self.assertRaisesRegex(
            OSError,
            "close failed",
        ):
            i2c.close()

        self.assertTrue(
            i2c.closed,
        )

    def test_bus_accessor_rejects_closed_bus(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        i2c.close()

        with self.assertRaisesRegex(
            I2CError,
            "bus is closed",
        ):
            i2c._bus()

    def test_address_accessor_rejects_missing_address(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C()

        with self.assertRaisesRegex(
            I2CError,
            "address is not set",
        ):
            i2c._address()

        i2c.close()

    def test_write_byte_retries_after_os_error(
        self,
    ) -> None:
        smbus = MagicMock()

        smbus.write_byte.side_effect = [
            OSError("first failure"),
            OSError("second failure"),
            None,
        ]

        with patch(
            "betabox_robotics.hardware.i2c.SMBus",
            return_value=smbus,
        ):
            i2c = I2C(
                address=0x14,
                retry_count=3,
            )

        i2c._write_byte(0x42)

        self.assertEqual(
            smbus.write_byte.call_count,
            3,
        )

        smbus.write_byte.assert_called_with(
            0x14,
            0x42,
        )

        i2c.close()

    def test_retry_exhaustion_raises_i2c_error(
        self,
    ) -> None:
        smbus = MagicMock()
        failure = OSError("write failed")

        smbus.write_byte.side_effect = failure

        with patch(
            "betabox_robotics.hardware.i2c.SMBus",
            return_value=smbus,
        ):
            i2c = I2C(
                address=0x14,
                retry_count=3,
            )

        with self.assertRaisesRegex(
            I2CError,
            "failed after 3 attempts",
        ) as raised:
            i2c._write_byte(0x42)

        self.assertEqual(
            smbus.write_byte.call_count,
            3,
        )

        self.assertIs(
            raised.exception.__cause__,
            failure,
        )

        i2c.close()

    def test_retry_does_not_catch_non_os_errors(
        self,
    ) -> None:
        smbus = MagicMock()
        failure = ValueError("invalid value")

        smbus.write_byte.side_effect = failure

        with patch(
            "betabox_robotics.hardware.i2c.SMBus",
            return_value=smbus,
        ):
            i2c = I2C(
                address=0x14,
                retry_count=3,
            )

        with self.assertRaisesRegex(
            ValueError,
            "invalid value",
        ):
            i2c._write_byte(0x42)

        smbus.write_byte.assert_called_once_with(
            0x14,
            0x42,
        )

        i2c.close()

    def test_write_single_byte_dispatch(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with patch.object(
            i2c,
            "_write_byte",
        ) as write_byte:
            i2c.write([0x42])

        write_byte.assert_called_once_with(0x42)

        i2c.close()

    def test_write_register_byte_dispatch(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with patch.object(
            i2c,
            "_write_byte_data",
        ) as write_byte_data:
            i2c.write(
                [
                    0x10,
                    0x42,
                ]
            )

        write_byte_data.assert_called_once_with(
            0x10,
            0x42,
        )

        i2c.close()

    def test_write_word_dispatch_uses_little_endian_data(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with patch.object(
            i2c,
            "_write_word_data",
        ) as write_word_data:
            i2c.write(
                [
                    0x10,
                    0x34,
                    0x12,
                ]
            )

        write_word_data.assert_called_once_with(
            0x10,
            0x1234,
        )

        i2c.close()

    def test_write_block_dispatch(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with patch.object(
            i2c,
            "_write_i2c_block_data",
        ) as write_block:
            i2c.write(
                [
                    0x10,
                    0x01,
                    0x02,
                    0x03,
                ]
            )

        write_block.assert_called_once_with(
            0x10,
            [
                0x01,
                0x02,
                0x03,
            ],
        )

        i2c.close()

    def test_read_one_byte(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with patch.object(
            i2c,
            "_read_byte",
            return_value=0x42,
        ) as read_byte:
            result = i2c.read()

        self.assertEqual(
            result,
            [0x42],
        )

        read_byte.assert_called_once_with()

        i2c.close()

    def test_read_multiple_bytes(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with patch.object(
            i2c,
            "_read_byte",
            side_effect=[
                0x01,
                0x02,
                0x03,
            ],
        ) as read_byte:
            result = i2c.read(3)

        self.assertEqual(
            result,
            [
                0x01,
                0x02,
                0x03,
            ],
        )

        self.assertEqual(
            read_byte.call_count,
            3,
        )

        i2c.close()

    def test_read_rejects_boolean_length(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with self.assertRaisesRegex(
            TypeError,
            "length must be an integer",
        ):
            i2c.read(True)

        i2c.close()

    def test_read_rejects_non_integer_length(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with self.assertRaisesRegex(
            TypeError,
            "length must be an integer",
        ):
            i2c.read(
                2.5  # type: ignore[arg-type]
            )

        i2c.close()

    def test_read_rejects_non_positive_length(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with self.assertRaisesRegex(
            ValueError,
            "greater than 0",
        ):
            i2c.read(0)

        i2c.close()

    def test_mem_write_dispatch(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with patch.object(
            i2c,
            "_write_i2c_block_data",
        ) as write_block:
            i2c.mem_write(
                [
                    0x01,
                    0x02,
                ],
                0x10,
            )

        write_block.assert_called_once_with(
            0x10,
            [
                0x01,
                0x02,
            ],
        )

        i2c.close()

    def test_mem_read_dispatch(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with patch.object(
            i2c,
            "_read_i2c_block_data",
            return_value=[
                0x01,
                0x02,
            ],
        ) as read_block:
            result = i2c.mem_read(
                2,
                0x10,
            )

        self.assertEqual(
            result,
            [
                0x01,
                0x02,
            ],
        )

        read_block.assert_called_once_with(
            0x10,
            2,
        )

        i2c.close()

    def test_mem_read_rejects_boolean_length(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with self.assertRaisesRegex(
            TypeError,
            "length must be an integer",
        ):
            i2c.mem_read(
                True,
                0x10,
            )

        i2c.close()

    def test_mem_read_rejects_non_positive_length(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with self.assertRaisesRegex(
            ValueError,
            "greater than 0",
        ):
            i2c.mem_read(
                0,
                0x10,
            )

        i2c.close()

    def test_normalizes_zero_integer(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        self.assertEqual(
            i2c._normalize_write_data(0),
            [0],
        )

        i2c.close()

    def test_normalizes_integer_to_little_endian_bytes(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        self.assertEqual(
            i2c._normalize_write_data(0x123456),
            [
                0x56,
                0x34,
                0x12,
            ],
        )

        i2c.close()

    def test_normalizes_bytearray(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        self.assertEqual(
            i2c._normalize_write_data(
                bytearray(
                    [
                        0x01,
                        0x02,
                    ]
                )
            ),
            [
                0x01,
                0x02,
            ],
        )

        i2c.close()

    def test_rejects_negative_integer_write_data(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with self.assertRaisesRegex(
            ValueError,
            "non-negative",
        ):
            i2c._normalize_write_data(-1)

        i2c.close()

    def test_rejects_invalid_write_data_type(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with self.assertRaisesRegex(
            TypeError,
            "write data must be",
        ):
            i2c._normalize_write_data(
                "bad"  # type: ignore[arg-type]
            )

        i2c.close()

    def test_scan_parses_detected_addresses(
        self,
    ) -> None:
        output = """\
     0 1 2 3 4 5 6 7 8 9 a b c d e f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- 14 -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --
"""

        completed = subprocess.CompletedProcess(
            args=[
                "i2cdetect",
                "-y",
                "1",
            ],
            returncode=0,
            stdout=output,
            stderr="",
        )

        with (
            patch("betabox_robotics.hardware.i2c.SMBus"),
            patch(
                "betabox_robotics.hardware.i2c.subprocess.run",
                return_value=completed,
            ) as run,
        ):
            i2c = I2C(
                address=0x14,
            )

            addresses = i2c.scan()

        self.assertEqual(
            addresses,
            [0x14],
        )

        run.assert_called_once_with(
            [
                "i2cdetect",
                "-y",
                "1",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        i2c.close()

    def test_scan_returns_sorted_unique_addresses(
        self,
    ) -> None:
        output = """\
         0 1 2 3 4 5 6 7 8 9 a b c d e f
    10: -- -- -- -- 14 -- -- -- -- -- -- -- -- -- -- --
    20: -- -- -- -- -- 25 -- -- -- -- -- -- -- -- -- --
    """

        completed = subprocess.CompletedProcess(
            args=["i2cdetect", "-y", "1"],
            returncode=0,
            stdout=output,
            stderr="",
        )

        with (
            patch("betabox_robotics.hardware.i2c.SMBus"),
            patch(
                "betabox_robotics.hardware.i2c.subprocess.run",
                return_value=completed,
            ),
        ):
            i2c = I2C(address=0x14)
            addresses = i2c.scan()

        self.assertEqual(
            addresses,
            [
                0x14,
                0x25,
            ],
        )

        i2c.close()

    def test_scan_raises_for_failed_command(
        self,
    ) -> None:
        completed = subprocess.CompletedProcess(
            args=[
                "i2cdetect",
            ],
            returncode=1,
            stdout="",
            stderr="permission denied",
        )

        with (
            patch("betabox_robotics.hardware.i2c.SMBus"),
            patch(
                "betabox_robotics.hardware.i2c.subprocess.run",
                return_value=completed,
            ),
        ):
            i2c = I2C(
                address=0x14,
            )

            with self.assertRaisesRegex(
                I2CError,
                "permission denied",
            ):
                i2c.scan()

        i2c.close()

    def test_scan_parses_kernel_claimed_address(
        self,
    ) -> None:
        output = """\
         0 1 2 3 4 5 6 7 8 9 a b c d e f
    00:          -- -- -- -- -- -- -- -- -- -- -- -- --
    10: -- -- -- -- UU -- -- -- -- -- -- -- -- -- -- --
    20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    """

        completed = subprocess.CompletedProcess(
            args=[
                "i2cdetect",
                "-y",
                "1",
            ],
            returncode=0,
            stdout=output,
            stderr="",
        )

        with (
            patch("betabox_robotics.hardware.i2c.SMBus"),
            patch(
                "betabox_robotics.hardware.i2c.subprocess.run",
                return_value=completed,
            ),
        ):
            i2c = I2C(
                address=0x14,
            )

            addresses = i2c.scan()

        self.assertEqual(
            addresses,
            [0x14],
        )

        i2c.close()

    def test_scan_ignores_unrecognized_cells(
        self,
    ) -> None:
        output = """\
         0 1 2 3 4 5 6 7 8 9 a b c d e f
    10: -- -- -- -- XX -- -- -- -- -- -- -- -- -- -- --
    20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    """

        completed = subprocess.CompletedProcess(
            args=[
                "i2cdetect",
                "-y",
                "1",
            ],
            returncode=0,
            stdout=output,
            stderr="",
        )

        with (
            patch("betabox_robotics.hardware.i2c.SMBus"),
            patch(
                "betabox_robotics.hardware.i2c.subprocess.run",
                return_value=completed,
            ),
        ):
            i2c = I2C(
                address=0x14,
            )

            addresses = i2c.scan()

        self.assertEqual(
            addresses,
            [],
        )

        i2c.close()

    def test_scan_wraps_command_launch_failure(
        self,
    ) -> None:
        failure = FileNotFoundError("i2cdetect not found")

        with (
            patch("betabox_robotics.hardware.i2c.SMBus"),
            patch(
                "betabox_robotics.hardware.i2c.subprocess.run",
                side_effect=failure,
            ),
        ):
            i2c = I2C(
                address=0x14,
            )

            with self.assertRaisesRegex(
                I2CError,
                "Unable to run i2cdetect",
            ) as raised:
                i2c.scan()

        self.assertIs(
            raised.exception.__cause__,
            failure,
        )

        i2c.close()

    def test_is_ready_returns_false_without_address(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C()

        with patch.object(
            i2c,
            "scan",
        ) as scan:
            self.assertFalse(i2c.is_ready())

        scan.assert_not_called()

        i2c.close()

    def test_is_ready_checks_scan_results(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with patch.object(
            i2c,
            "scan",
            return_value=[
                0x14,
            ],
        ):
            self.assertTrue(i2c.is_ready())

        with patch.object(
            i2c,
            "scan",
            return_value=[],
        ):
            self.assertFalse(i2c.is_ready())

        i2c.close()

    def test_is_available_delegates_to_is_ready(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        with patch.object(
            i2c,
            "is_ready",
            return_value=True,
        ) as is_ready:
            result = i2c.is_available()

        self.assertTrue(result)

        is_ready.assert_called_once_with()

        i2c.close()

    def test_context_manager_returns_self_and_closes(
        self,
    ) -> None:
        smbus = MagicMock()

        with patch(
            "betabox_robotics.hardware.i2c.SMBus",
            return_value=smbus,
        ):
            i2c = I2C(
                address=0x14,
            )

            with i2c as entered:
                self.assertIs(
                    entered,
                    i2c,
                )
                self.assertFalse(
                    i2c.closed,
                )

        smbus.close.assert_called_once_with()

        self.assertTrue(
            i2c.closed,
        )

    def test_closed_bus_cannot_reenter_context(
        self,
    ) -> None:
        with patch("betabox_robotics.hardware.i2c.SMBus"):
            i2c = I2C(
                address=0x14,
            )

        i2c.close()

        with (
            self.assertRaisesRegex(
                I2CError,
                "closed I2C bus",
            ),
            i2c,
        ):
            pass

    def test_tuple_address_candidates_are_accepted(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.hardware.i2c.SMBus"),
            patch.object(
                I2C,
                "scan",
                return_value=[
                    0x15,
                ],
            ),
        ):
            i2c = I2C(
                address=(
                    0x14,
                    0x15,
                ),
            )

        self.assertEqual(
            i2c.address,
            0x15,
        )

        i2c.close()

    def test_empty_tuple_address_candidates_are_rejected(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.hardware.i2c.SMBus") as smbus_type,
            self.assertRaisesRegex(
                ValueError,
                "candidate sequence cannot be empty",
            ),
        ):
            I2C(
                address=(),
            )

        smbus_type.assert_not_called()

    def test_invalid_tuple_address_candidate_is_rejected(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.hardware.i2c.SMBus") as smbus_type,
            self.assertRaisesRegex(
                ValueError,
                "between 0x00 and 0x7F",
            ),
        ):
            I2C(
                address=(
                    0x14,
                    0x80,
                ),
            )

        smbus_type.assert_not_called()

    def test_tuple_candidate_selection_preserves_order(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.hardware.i2c.SMBus"),
            patch.object(
                I2C,
                "scan",
                return_value=[
                    0x16,
                    0x15,
                ],
            ) as scan,
        ):
            i2c = I2C(
                address=(
                    0x14,
                    0x15,
                    0x16,
                ),
            )

        scan.assert_called_once_with()

        self.assertEqual(
            i2c.address,
            0x15,
        )

        i2c.close()

    def test_tuple_candidate_sequence_preserves_first_address_fallback(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.hardware.i2c.SMBus"),
            patch.object(
                I2C,
                "scan",
                return_value=[],
            ),
        ):
            i2c = I2C(
                address=(
                    0x14,
                    0x15,
                ),
            )

        self.assertEqual(
            i2c.address,
            0x14,
        )

        i2c.close()


if __name__ == "__main__":
    unittest.main()
