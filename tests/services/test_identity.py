from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from betabox_robotics.services.identity import (
    _validate_length,
    _validate_optional_string,
    _validate_prefix,
    get_serial,
    identity_name,
    serial_suffix,
)

MODULE = "betabox_robotics.services.identity"


class ValidateLengthTests(unittest.TestCase):
    def test_accepts_positive_integer(self) -> None:
        self.assertEqual(
            _validate_length(4),
            4,
        )

    def test_accepts_one(self) -> None:
        self.assertEqual(
            _validate_length(1),
            1,
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
                    "length must be an integer",
                ),
            ):
                _validate_length(value)

    def test_rejects_non_integer(self) -> None:
        for value in (
            4.0,
            "4",
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "length must be an integer",
                ),
            ):
                _validate_length(value)

    def test_rejects_non_positive_integer(self) -> None:
        for value in (
            0,
            -1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "length must be greater than 0",
                ),
            ):
                _validate_length(value)


class ValidatePrefixTests(unittest.TestCase):
    def test_accepts_and_normalizes_prefix(self) -> None:
        self.assertEqual(
            _validate_prefix(" Betabox "),
            "Betabox",
        )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            123,
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "prefix must be a string",
                ),
            ):
                _validate_prefix(value)

    def test_rejects_empty_prefix(self) -> None:
        for value in (
            "",
            "   ",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "prefix cannot be empty",
                ),
            ):
                _validate_prefix(value)


class ValidateOptionalStringTests(unittest.TestCase):
    def test_none_returns_none(self) -> None:
        self.assertIsNone(
            _validate_optional_string(
                None,
                name="fallback",
            )
        )

    def test_accepts_and_normalizes_string(self) -> None:
        self.assertEqual(
            _validate_optional_string(
                " unknown ",
                name="fallback",
            ),
            "unknown",
        )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            123,
            True,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "fallback must be a string or None",
                ),
            ):
                _validate_optional_string(
                    value,
                    name="fallback",
                )

    def test_rejects_empty_string(self) -> None:
        for value in (
            "",
            "   ",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "fallback cannot be empty",
                ),
            ):
                _validate_optional_string(
                    value,
                    name="fallback",
                )


class GetSerialTests(unittest.TestCase):
    def test_prefers_device_tree_serial(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            device_tree = root / "serial-number"
            cpuinfo = root / "cpuinfo"

            device_tree.write_text(
                "00000000abcdef12\x00\n",
                encoding="utf-8",
            )
            cpuinfo.write_text(
                "Serial : should-not-be-used\n",
                encoding="utf-8",
            )

            with (
                patch(
                    f"{MODULE}.DEVICE_TREE_SERIAL_PATH",
                    device_tree,
                ),
                patch(
                    f"{MODULE}.CPUINFO_PATH",
                    cpuinfo,
                ),
            ):
                result = get_serial()

        self.assertEqual(
            result,
            "00000000abcdef12",
        )

    def test_uses_cpuinfo_when_device_tree_is_missing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            device_tree = root / "missing-serial"
            cpuinfo = root / "cpuinfo"

            cpuinfo.write_text(
                "processor\t: 0\nHardware\t: BCM2711\nSerial\t\t: 00000000abcdef12\n",
                encoding="utf-8",
            )

            with (
                patch(
                    f"{MODULE}.DEVICE_TREE_SERIAL_PATH",
                    device_tree,
                ),
                patch(
                    f"{MODULE}.CPUINFO_PATH",
                    cpuinfo,
                ),
            ):
                result = get_serial()

        self.assertEqual(
            result,
            "00000000abcdef12",
        )

    def test_uses_cpuinfo_when_device_tree_is_empty(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            device_tree = root / "serial-number"
            cpuinfo = root / "cpuinfo"

            device_tree.write_text(
                "\x00\n",
                encoding="utf-8",
            )
            cpuinfo.write_text(
                "Serial : abcdef12\n",
                encoding="utf-8",
            )

            with (
                patch(
                    f"{MODULE}.DEVICE_TREE_SERIAL_PATH",
                    device_tree,
                ),
                patch(
                    f"{MODULE}.CPUINFO_PATH",
                    cpuinfo,
                ),
            ):
                result = get_serial()

        self.assertEqual(
            result,
            "abcdef12",
        )

    def test_uses_cpuinfo_after_device_tree_read_error(
        self,
    ) -> None:
        device_tree = MagicMock()
        device_tree.is_file.return_value = True
        device_tree.read_text.side_effect = OSError("device-tree read failed")

        with tempfile.TemporaryDirectory() as temp_dir:
            cpuinfo = Path(temp_dir) / "cpuinfo"
            cpuinfo.write_text(
                "Serial : abcdef12\n",
                encoding="utf-8",
            )

            with (
                patch(
                    f"{MODULE}.DEVICE_TREE_SERIAL_PATH",
                    device_tree,
                ),
                patch(
                    f"{MODULE}.CPUINFO_PATH",
                    cpuinfo,
                ),
            ):
                result = get_serial()

        self.assertEqual(
            result,
            "abcdef12",
        )
        device_tree.is_file.assert_called_once_with()
        device_tree.read_text.assert_called_once_with(
            encoding="utf-8",
            errors="ignore",
        )

    def test_returns_none_after_cpuinfo_read_error(
        self,
    ) -> None:
        cpuinfo = MagicMock()
        cpuinfo.is_file.return_value = True
        cpuinfo.read_text.side_effect = OSError("cpuinfo read failed")

        with tempfile.TemporaryDirectory() as temp_dir:
            device_tree = Path(temp_dir) / "missing-device-tree"

            with (
                patch(
                    f"{MODULE}.DEVICE_TREE_SERIAL_PATH",
                    device_tree,
                ),
                patch(
                    f"{MODULE}.CPUINFO_PATH",
                    cpuinfo,
                ),
            ):
                result = get_serial()

        self.assertIsNone(result)
        cpuinfo.is_file.assert_called_once_with()
        cpuinfo.read_text.assert_called_once_with(
            encoding="utf-8",
            errors="ignore",
        )

    def test_returns_none_when_files_are_missing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            with (
                patch(
                    f"{MODULE}.DEVICE_TREE_SERIAL_PATH",
                    root / "missing-device-tree",
                ),
                patch(
                    f"{MODULE}.CPUINFO_PATH",
                    root / "missing-cpuinfo",
                ),
            ):
                result = get_serial()

        self.assertIsNone(result)

    def test_ignores_cpuinfo_lines_without_serial(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cpuinfo = root / "cpuinfo"

            cpuinfo.write_text(
                "processor : 0\nHardware : BCM2711\n",
                encoding="utf-8",
            )

            with (
                patch(
                    f"{MODULE}.DEVICE_TREE_SERIAL_PATH",
                    root / "missing-device-tree",
                ),
                patch(
                    f"{MODULE}.CPUINFO_PATH",
                    cpuinfo,
                ),
            ):
                result = get_serial()

        self.assertIsNone(result)

    def test_ignores_empty_cpuinfo_serial(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cpuinfo = root / "cpuinfo"

            cpuinfo.write_text(
                "Serial :   \n",
                encoding="utf-8",
            )

            with (
                patch(
                    f"{MODULE}.DEVICE_TREE_SERIAL_PATH",
                    root / "missing-device-tree",
                ),
                patch(
                    f"{MODULE}.CPUINFO_PATH",
                    cpuinfo,
                ),
            ):
                result = get_serial()

        self.assertIsNone(result)

    def test_ignores_non_serial_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cpuinfo = root / "cpuinfo"

            cpuinfo.write_text(
                "NotSerial : abcdef12\n",
                encoding="utf-8",
            )

            with (
                patch(
                    f"{MODULE}.DEVICE_TREE_SERIAL_PATH",
                    root / "missing-device-tree",
                ),
                patch(
                    f"{MODULE}.CPUINFO_PATH",
                    cpuinfo,
                ),
            ):
                result = get_serial()

        self.assertIsNone(result)


class SerialSuffixTests(unittest.TestCase):
    def test_returns_requested_suffix(self) -> None:
        with patch(
            f"{MODULE}.get_serial",
            return_value="00000000abcdef12",
        ):
            result = serial_suffix(4)

        self.assertEqual(
            result,
            "ef12",
        )

    def test_returns_entire_serial_when_length_is_longer(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.get_serial",
            return_value="abcd",
        ):
            result = serial_suffix(10)

        self.assertEqual(
            result,
            "abcd",
        )

    def test_returns_none_when_serial_is_missing(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.get_serial",
            return_value=None,
        ):
            result = serial_suffix()

        self.assertIsNone(result)

    def test_returns_normalized_fallback(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.get_serial",
            return_value=None,
        ):
            result = serial_suffix(fallback=" unknown ")

        self.assertEqual(
            result,
            "unknown",
        )

    def test_serial_takes_precedence_over_fallback(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.get_serial",
            return_value="abcdef12",
        ):
            result = serial_suffix(
                4,
                fallback="unknown",
            )

        self.assertEqual(
            result,
            "ef12",
        )

    def test_validates_length_before_reading_serial(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.get_serial") as get_serial_mock,
            self.assertRaisesRegex(
                TypeError,
                "length must be an integer",
            ),
        ):
            serial_suffix(
                True  # type: ignore[arg-type]
            )

        get_serial_mock.assert_not_called()

    def test_validates_fallback_before_reading_serial(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.get_serial") as get_serial_mock,
            self.assertRaisesRegex(
                ValueError,
                "fallback cannot be empty",
            ),
        ):
            serial_suffix(fallback=" ")

        get_serial_mock.assert_not_called()


class IdentityNameTests(unittest.TestCase):
    def test_builds_identity_name(self) -> None:
        with patch(
            f"{MODULE}.serial_suffix",
            return_value="7eea",
        ) as suffix:
            result = identity_name("Betabox")

        self.assertEqual(
            result,
            "Betabox-7eea",
        )
        suffix.assert_called_once_with(
            4,
            fallback=None,
        )

    def test_normalizes_prefix_and_fallback(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.serial_suffix",
            return_value="unknown",
        ) as suffix:
            result = identity_name(
                " Betabox ",
                suffix_length=6,
                fallback=" unknown ",
            )

        self.assertEqual(
            result,
            "Betabox-unknown",
        )
        suffix.assert_called_once_with(
            6,
            fallback="unknown",
        )

    def test_returns_none_without_serial_or_fallback(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.serial_suffix",
            return_value=None,
        ):
            result = identity_name("Betabox")

        self.assertIsNone(result)

    def test_rejects_invalid_prefix_before_suffix_lookup(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.serial_suffix") as suffix,
            self.assertRaisesRegex(
                ValueError,
                "prefix cannot be empty",
            ),
        ):
            identity_name(" ")

        suffix.assert_not_called()

    def test_rejects_invalid_fallback_before_suffix_lookup(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.serial_suffix") as suffix,
            self.assertRaisesRegex(
                TypeError,
                "fallback must be a string or None",
            ),
        ):
            identity_name(
                "Betabox",
                fallback=123,  # type: ignore[arg-type]
            )

        suffix.assert_not_called()

    def test_forwards_suffix_length_validation(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "length must be greater than 0",
        ):
            identity_name(
                "Betabox",
                suffix_length=0,
            )


if __name__ == "__main__":
    unittest.main()
