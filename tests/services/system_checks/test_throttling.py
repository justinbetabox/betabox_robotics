from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from betabox_robotics.services.system_checks.throttling import (
    collect_throttling_status,
)

MODULE = "betabox_robotics.services.system_checks.throttling"


def make_result(
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[
            "vcgencmd",
            "get_throttled",
        ],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


class CollectThrottlingStatusTests(unittest.TestCase):
    def test_runs_vcgencmd(self) -> None:
        result = make_result(stdout="throttled=0x0\n")

        with patch(
            f"{MODULE}.run",
            return_value=result,
        ) as run:
            status = collect_throttling_status()

        run.assert_called_once_with(
            [
                "vcgencmd",
                "get_throttled",
            ],
            timeout=5,
        )

        self.assertEqual(
            status.raw,
            "0x0",
        )
        self.assertIsNone(status.error)

    def test_reports_no_throttling_flags(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(stdout="throttled=0x0"),
        ):
            status = collect_throttling_status()

        self.assertEqual(
            status.raw,
            "0x0",
        )
        self.assertFalse(status.undervoltage_now)
        self.assertFalse(status.undervoltage_occurred)
        self.assertFalse(status.throttled_now)
        self.assertFalse(status.throttled_occurred)
        self.assertIsNone(status.error)

    def test_detects_undervoltage_now(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(stdout="throttled=0x1"),
        ):
            status = collect_throttling_status()

        self.assertTrue(status.undervoltage_now)
        self.assertFalse(status.throttled_now)
        self.assertFalse(status.undervoltage_occurred)
        self.assertFalse(status.throttled_occurred)

    def test_detects_throttled_now(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(stdout="throttled=0x4"),
        ):
            status = collect_throttling_status()

        self.assertFalse(status.undervoltage_now)
        self.assertTrue(status.throttled_now)
        self.assertFalse(status.undervoltage_occurred)
        self.assertFalse(status.throttled_occurred)

    def test_detects_undervoltage_occurred(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(stdout="throttled=0x10000"),
        ):
            status = collect_throttling_status()

        self.assertFalse(status.undervoltage_now)
        self.assertFalse(status.throttled_now)
        self.assertTrue(status.undervoltage_occurred)
        self.assertFalse(status.throttled_occurred)

    def test_detects_throttled_occurred(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(stdout="throttled=0x40000"),
        ):
            status = collect_throttling_status()

        self.assertFalse(status.undervoltage_now)
        self.assertFalse(status.throttled_now)
        self.assertFalse(status.undervoltage_occurred)
        self.assertTrue(status.throttled_occurred)

    def test_detects_all_supported_flags(self) -> None:
        value = (1 << 0) | (1 << 2) | (1 << 16) | (1 << 18)

        with patch(
            f"{MODULE}.run",
            return_value=make_result(stdout=f"throttled=0x{value:x}"),
        ):
            status = collect_throttling_status()

        self.assertTrue(status.undervoltage_now)
        self.assertTrue(status.throttled_now)
        self.assertTrue(status.undervoltage_occurred)
        self.assertTrue(status.throttled_occurred)
        self.assertEqual(
            status.raw,
            f"0x{value:x}",
        )

    def test_ignores_unrepresented_flag_bits(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(stdout="throttled=0x2"),
        ):
            status = collect_throttling_status()

        self.assertEqual(
            status.raw,
            "0x2",
        )
        self.assertFalse(status.undervoltage_now)
        self.assertFalse(status.throttled_now)
        self.assertFalse(status.undervoltage_occurred)
        self.assertFalse(status.throttled_occurred)

    def test_normalizes_uppercase_hexadecimal(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(stdout="throttled=0xA"),
        ):
            status = collect_throttling_status()

        self.assertEqual(
            status.raw,
            "0xa",
        )

    def test_accepts_hex_value_without_0x_prefix(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(stdout="throttled=40000"),
        ):
            status = collect_throttling_status()

        self.assertEqual(
            status.raw,
            "0x40000",
        )
        self.assertTrue(status.throttled_occurred)

    def test_strips_output_whitespace(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(stdout=("  throttled=0x1  \n")),
        ):
            status = collect_throttling_status()

        self.assertEqual(
            status.raw,
            "0x1",
        )
        self.assertTrue(status.undervoltage_now)

    def test_strips_prefix_and_value_whitespace(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(stdout=(" throttled = 0x4 ")),
        ):
            status = collect_throttling_status()

        self.assertEqual(
            status.raw,
            "0x4",
        )
        self.assertTrue(status.throttled_now)

    def test_returns_error_when_command_cannot_run(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=None,
        ):
            status = collect_throttling_status()

        self.assertIsNone(status.raw)
        self.assertFalse(status.undervoltage_now)
        self.assertFalse(status.undervoltage_occurred)
        self.assertFalse(status.throttled_now)
        self.assertFalse(status.throttled_occurred)
        self.assertEqual(
            status.error,
            "vcgencmd get_throttled failed",
        )

    def test_returns_error_for_nonzero_exit(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=1,
                stderr="command failed",
            ),
        ):
            status = collect_throttling_status()

        self.assertIsNone(status.raw)
        self.assertEqual(
            status.error,
            "vcgencmd get_throttled failed",
        )

    def test_rejects_output_without_separator(
        self,
    ) -> None:
        output = "throttled 0x1"

        with patch(
            f"{MODULE}.run",
            return_value=make_result(stdout=output),
        ):
            status = collect_throttling_status()

        self.assertEqual(
            status.raw,
            output,
        )
        self.assertEqual(
            status.error,
            "invalid vcgencmd response",
        )
        self.assertFalse(status.undervoltage_now)

    def test_rejects_wrong_response_prefix(self) -> None:
        output = "status=0x1"

        with patch(
            f"{MODULE}.run",
            return_value=make_result(stdout=output),
        ):
            status = collect_throttling_status()

        self.assertEqual(
            status.raw,
            output,
        )
        self.assertEqual(
            status.error,
            "invalid vcgencmd response",
        )

    def test_rejects_empty_response_value(self) -> None:
        output = "throttled="

        with patch(
            f"{MODULE}.run",
            return_value=make_result(stdout=output),
        ):
            status = collect_throttling_status()

        self.assertEqual(
            status.raw,
            output,
        )
        self.assertEqual(
            status.error,
            "invalid vcgencmd response",
        )

    def test_rejects_whitespace_response_value(
        self,
    ) -> None:
        output = "throttled=   "

        with patch(
            f"{MODULE}.run",
            return_value=make_result(stdout=output),
        ):
            status = collect_throttling_status()

        self.assertEqual(
            status.raw,
            "throttled=",
        )
        self.assertEqual(
            status.error,
            "invalid vcgencmd response",
        )

    def test_reports_invalid_hexadecimal_value(
        self,
    ) -> None:
        output = "throttled=invalid"

        with patch(
            f"{MODULE}.run",
            return_value=make_result(stdout=output),
        ):
            status = collect_throttling_status()

        self.assertEqual(
            status.raw,
            output,
        )
        self.assertFalse(status.undervoltage_now)
        self.assertFalse(status.undervoltage_occurred)
        self.assertFalse(status.throttled_now)
        self.assertFalse(status.throttled_occurred)
        self.assertIsNotNone(status.error)

    def test_unexpected_command_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.run",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_throttling_status()

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
