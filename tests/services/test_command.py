from __future__ import annotations

import math
import subprocess
import unittest
from unittest.mock import patch

from betabox_robotics.services.command import (
    _validate_command,
    _validate_timeout,
    run,
)

MODULE = "betabox_robotics.services.command"


class ValidateCommandTests(unittest.TestCase):
    def test_accepts_and_normalizes_command(self) -> None:
        self.assertEqual(
            _validate_command(
                [
                    " i2cdetect ",
                    " -y ",
                    " 1 ",
                ]
            ),
            [
                "i2cdetect",
                "-y",
                "1",
            ],
        )

    def test_returns_new_list(self) -> None:
        command = [
            "aplay",
            "-l",
        ]

        result = _validate_command(command)

        self.assertEqual(
            result,
            command,
        )
        self.assertIsNot(
            result,
            command,
        )

    def test_rejects_non_list(self) -> None:
        for value in (
            None,
            "aplay",
            (
                "aplay",
                "-l",
            ),
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "command must be a list of strings",
                ),
            ):
                _validate_command(value)

    def test_rejects_empty_command(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "command cannot be empty",
        ):
            _validate_command([])

    def test_rejects_non_string_argument(self) -> None:
        for value in (
            1,
            True,
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("command must contain only strings"),
                ),
            ):
                _validate_command(
                    [
                        "command",
                        value,  # type: ignore[list-item]
                    ]
                )

    def test_rejects_empty_argument(self) -> None:
        for value in (
            "",
            "   ",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    ("command cannot contain empty strings"),
                ),
            ):
                _validate_command(
                    [
                        "command",
                        value,
                    ]
                )


class ValidateTimeoutTests(unittest.TestCase):
    def test_accepts_positive_integer(self) -> None:
        self.assertEqual(
            _validate_timeout(5),
            5.0,
        )

    def test_accepts_positive_float(self) -> None:
        self.assertEqual(
            _validate_timeout(0.5),
            0.5,
        )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            True,
            False,
            "5",
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "timeout must be a number",
                ),
            ):
                _validate_timeout(value)

    def test_rejects_non_finite_value(self) -> None:
        for value in (
            math.inf,
            -math.inf,
            math.nan,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "timeout must be finite",
                ),
            ):
                _validate_timeout(value)

    def test_rejects_non_positive_value(self) -> None:
        for value in (
            0,
            0.0,
            -1,
            -0.5,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    ("timeout must be greater than 0"),
                ),
            ):
                _validate_timeout(value)


class RunTests(unittest.TestCase):
    def test_runs_normalized_command(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[
                "printf",
                "ok",
            ],
            returncode=0,
            stdout="ok",
            stderr="",
        )

        with patch(
            f"{MODULE}.subprocess.run",
            return_value=completed,
        ) as subprocess_run:
            result = run(
                [
                    " printf ",
                    " ok ",
                ],
                timeout=2,
            )

        self.assertIs(
            result,
            completed,
        )
        subprocess_run.assert_called_once_with(
            [
                "printf",
                "ok",
            ],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )

    def test_uses_default_timeout(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[
                "true",
            ],
            returncode=0,
            stdout="",
            stderr="",
        )

        with patch(
            f"{MODULE}.subprocess.run",
            return_value=completed,
        ) as subprocess_run:
            result = run(
                [
                    "true",
                ]
            )

        self.assertIs(
            result,
            completed,
        )
        subprocess_run.assert_called_once_with(
            [
                "true",
            ],
            capture_output=True,
            text=True,
            timeout=5.0,
            check=False,
        )

    def test_returns_nonzero_completed_process(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[
                "false",
            ],
            returncode=1,
            stdout="",
            stderr="failed",
        )

        with patch(
            f"{MODULE}.subprocess.run",
            return_value=completed,
        ):
            result = run(
                [
                    "false",
                ]
            )

        self.assertIs(
            result,
            completed,
        )
        self.assertEqual(
            result.returncode,
            1,
        )

    def test_returns_none_for_os_error(self) -> None:
        with patch(
            f"{MODULE}.subprocess.run",
            side_effect=OSError("command not found"),
        ):
            result = run(
                [
                    "missing-command",
                ]
            )

        self.assertIsNone(result)

    def test_returns_none_for_timeout(self) -> None:
        error = subprocess.TimeoutExpired(
            cmd=[
                "slow-command",
            ],
            timeout=1.0,
        )

        with patch(
            f"{MODULE}.subprocess.run",
            side_effect=error,
        ):
            result = run(
                [
                    "slow-command",
                ],
                timeout=1,
            )

        self.assertIsNone(result)

    def test_unexpected_exception_propagates(self) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.subprocess.run",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            run(
                [
                    "command",
                ]
            )

        self.assertIs(
            context.exception,
            error,
        )

    def test_validates_command_before_subprocess(self) -> None:
        with (
            patch(f"{MODULE}.subprocess.run") as subprocess_run,
            self.assertRaisesRegex(
                ValueError,
                "command cannot be empty",
            ),
        ):
            run([])

        subprocess_run.assert_not_called()

    def test_validates_timeout_before_subprocess(self) -> None:
        with (
            patch(f"{MODULE}.subprocess.run") as subprocess_run,
            self.assertRaisesRegex(
                TypeError,
                "timeout must be a number",
            ),
        ):
            run(
                [
                    "command",
                ],
                timeout=True,
            )

        subprocess_run.assert_not_called()

    def test_command_validation_happens_before_timeout(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}._validate_timeout") as validate_timeout,
            self.assertRaisesRegex(
                ValueError,
                "command cannot be empty",
            ),
        ):
            run(
                [],
                timeout=True,
            )

        validate_timeout.assert_not_called()


if __name__ == "__main__":
    unittest.main()
