from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.hardware_checks.i2c import (
    _validate_config,
    collect_i2c_status,
)

MODULE = "betabox_robotics.services.hardware_checks.i2c"


class ValidateConfigTests(unittest.TestCase):
    def test_accepts_platform_config(self) -> None:
        result = _validate_config(DEFAULT_PLATFORM_CONFIG)

        self.assertIs(
            result,
            DEFAULT_PLATFORM_CONFIG,
        )

    def test_rejects_invalid_config(self) -> None:
        for value in (
            None,
            object(),
            "config",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "config must be a PlatformConfig",
                ),
            ):
                _validate_config(value)


class CollectI2CStatusTests(unittest.TestCase):
    def test_returns_unavailable_when_device_is_missing(
        self,
    ) -> None:
        device = DEFAULT_PLATFORM_CONFIG.verification.i2c_device

        with (
            patch.object(
                Path,
                "exists",
                return_value=False,
            ) as exists,
            patch(f"{MODULE}.run") as run,
        ):
            status = collect_i2c_status()

        self.assertFalse(status.available)
        self.assertEqual(
            status.devices,
            (),
        )
        self.assertEqual(
            status.error,
            f"{device} is missing",
        )
        exists.assert_called_once_with()
        run.assert_not_called()

    def test_runs_i2cdetect_with_configured_bus_and_timeout(
        self,
    ) -> None:
        completed = subprocess.CompletedProcess(
            args=[
                "i2cdetect",
                "-y",
                "1",
            ],
            returncode=0,
            stdout="",
            stderr="",
        )

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch(
                f"{MODULE}.run",
                return_value=completed,
            ) as run,
        ):
            status = collect_i2c_status()

        self.assertTrue(status.available)
        self.assertEqual(
            status.devices,
            (),
        )
        self.assertIsNone(status.error)

        run.assert_called_once_with(
            [
                "i2cdetect",
                "-y",
                str(DEFAULT_PLATFORM_CONFIG.verification.i2c_bus),
            ],
            timeout=(DEFAULT_PLATFORM_CONFIG.verification.command_timeout_seconds),
        )

    def test_returns_error_when_command_cannot_run(
        self,
    ) -> None:
        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch(
                f"{MODULE}.run",
                return_value=None,
            ),
        ):
            status = collect_i2c_status()

        self.assertTrue(status.available)
        self.assertEqual(
            status.devices,
            (),
        )
        self.assertEqual(
            status.error,
            "could not run i2cdetect",
        )

    def test_returns_stderr_for_failed_command(
        self,
    ) -> None:
        completed = subprocess.CompletedProcess(
            args=[
                "i2cdetect",
                "-y",
                "1",
            ],
            returncode=1,
            stdout="",
            stderr=" permission denied \n",
        )

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch(
                f"{MODULE}.run",
                return_value=completed,
            ),
        ):
            status = collect_i2c_status()

        self.assertTrue(status.available)
        self.assertEqual(
            status.devices,
            (),
        )
        self.assertEqual(
            status.error,
            "permission denied",
        )

    def test_uses_fallback_for_failed_command_without_stderr(
        self,
    ) -> None:
        completed = subprocess.CompletedProcess(
            args=[
                "i2cdetect",
                "-y",
                "1",
            ],
            returncode=1,
            stdout="",
            stderr="   ",
        )

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch(
                f"{MODULE}.run",
                return_value=completed,
            ),
        ):
            status = collect_i2c_status()

        self.assertEqual(
            status.error,
            "i2cdetect failed",
        )

    def test_parses_detected_devices(self) -> None:
        output = """
             0  1  2  3  4  5  6  7
        00:          -- -- -- -- -- --
        10: -- -- -- -- 14 -- -- --
        20: -- -- -- -- -- -- -- --
        40: 40 -- -- -- -- -- -- --
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
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch(
                f"{MODULE}.run",
                return_value=completed,
            ),
        ):
            status = collect_i2c_status()

        self.assertTrue(status.available)
        self.assertEqual(
            status.devices,
            (
                "0x14",
                "0x40",
            ),
        )
        self.assertIsNone(status.error)

    def test_normalizes_uppercase_hex_values(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[
                "i2cdetect",
                "-y",
                "1",
            ],
            returncode=0,
            stdout="10: -- -- 1A -- -- -- -- --\n",
            stderr="",
        )

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch(
                f"{MODULE}.run",
                return_value=completed,
            ),
        ):
            status = collect_i2c_status()

        self.assertEqual(
            status.devices,
            ("0x1a",),
        )

    def test_sorts_and_deduplicates_devices(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[
                "i2cdetect",
                "-y",
                "1",
            ],
            returncode=0,
            stdout=("10: 40 14 40 -- -- -- -- --\n"),
            stderr="",
        )

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch(
                f"{MODULE}.run",
                return_value=completed,
            ),
        ):
            status = collect_i2c_status()

        self.assertEqual(
            status.devices,
            (
                "0x14",
                "0x40",
            ),
        )

    def test_ignores_lines_without_separator(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[
                "i2cdetect",
                "-y",
                "1",
            ],
            returncode=0,
            stdout=("header without separator\n10: 14 -- -- -- -- -- -- --\n"),
            stderr="",
        )

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch(
                f"{MODULE}.run",
                return_value=completed,
            ),
        ):
            status = collect_i2c_status()

        self.assertEqual(
            status.devices,
            ("0x14",),
        )

    def test_ignores_invalid_tokens(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[
                "i2cdetect",
                "-y",
                "1",
            ],
            returncode=0,
            stdout=("10: -- ZZ 123 G1 14 UU -- --\n"),
            stderr="",
        )

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch(
                f"{MODULE}.run",
                return_value=completed,
            ),
        ):
            status = collect_i2c_status()

        self.assertEqual(
            status.devices,
            ("0x14",),
        )

    def test_accepts_reserved_uu_token_as_non_device(
        self,
    ) -> None:
        completed = subprocess.CompletedProcess(
            args=[
                "i2cdetect",
                "-y",
                "1",
            ],
            returncode=0,
            stdout=("10: UU -- -- 14 -- -- -- --\n"),
            stderr="",
        )

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch(
                f"{MODULE}.run",
                return_value=completed,
            ),
        ):
            status = collect_i2c_status()

        self.assertEqual(
            status.devices,
            ("0x14",),
        )

    def test_empty_output_returns_available_without_devices(
        self,
    ) -> None:
        completed = subprocess.CompletedProcess(
            args=[
                "i2cdetect",
                "-y",
                "1",
            ],
            returncode=0,
            stdout="",
            stderr="",
        )

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch(
                f"{MODULE}.run",
                return_value=completed,
            ),
        ):
            status = collect_i2c_status()

        self.assertTrue(status.available)
        self.assertEqual(
            status.devices,
            (),
        )
        self.assertIsNone(status.error)

    def test_rejects_invalid_config_before_filesystem_check(
        self,
    ) -> None:
        with (
            patch.object(
                Path,
                "exists",
            ) as exists,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            collect_i2c_status(
                object()  # type: ignore[arg-type]
            )

        exists.assert_not_called()


if __name__ == "__main__":
    unittest.main()
