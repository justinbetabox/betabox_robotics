from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import call, patch

from betabox_robotics.services.privileges import (
    BETABOX_EXECUTABLE,
    SUDO_EXECUTABLE,
    _require_executable,
    _validate_arguments,
    elevate_betabox,
    require_root_or_elevate,
    running_as_root,
)

MODULE = "betabox_robotics.services.privileges"


class ValidateArgumentsTests(unittest.TestCase):
    def test_accepts_and_normalizes_arguments(self) -> None:
        self.assertEqual(
            _validate_arguments(
                [
                    " status ",
                    "--full",
                ]
            ),
            [
                "status",
                "--full",
            ],
        )

    def test_accepts_empty_list(self) -> None:
        self.assertEqual(
            _validate_arguments([]),
            [],
        )

    def test_returns_new_list(self) -> None:
        arguments = [
            "status",
        ]

        result = _validate_arguments(arguments)

        self.assertEqual(
            result,
            arguments,
        )
        self.assertIsNot(
            result,
            arguments,
        )

    def test_rejects_non_list(self) -> None:
        for value in (
            None,
            "status",
            ("status",),
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "arguments must be a list of strings",
                ),
            ):
                _validate_arguments(value)

    def test_rejects_non_string_entries(self) -> None:
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
                    "arguments must contain only strings",
                ),
            ):
                _validate_arguments(
                    [
                        "status",
                        value,  # type: ignore[list-item]
                    ]
                )

    def test_rejects_empty_entries(self) -> None:
        for value in (
            "",
            "   ",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "arguments cannot contain empty strings",
                ),
            ):
                _validate_arguments(
                    [
                        value,
                    ]
                )


class RequireExecutableTests(unittest.TestCase):
    def test_accepts_executable_file(self) -> None:
        path = Path("/usr/bin/example")

        with (
            patch.object(
                Path,
                "is_file",
                return_value=True,
            ) as is_file,
            patch(
                f"{MODULE}.os.access",
                return_value=True,
            ) as access,
        ):
            result = _require_executable(
                path,
                name="Example",
            )

        self.assertIsNone(result)
        is_file.assert_called_once_with()
        access.assert_called_once_with(
            path,
            1,
        )

    def test_rejects_missing_file(self) -> None:
        path = Path("/missing/example")

        with (
            patch.object(
                Path,
                "is_file",
                return_value=False,
            ),
            patch(f"{MODULE}.os.access") as access,
            self.assertRaisesRegex(
                RuntimeError,
                "Example is missing: /missing/example",
            ),
        ):
            _require_executable(
                path,
                name="Example",
            )

        access.assert_not_called()

    def test_rejects_non_executable_file(self) -> None:
        path = Path("/usr/bin/example")

        with (
            patch.object(
                Path,
                "is_file",
                return_value=True,
            ),
            patch(
                f"{MODULE}.os.access",
                return_value=False,
            ),
            self.assertRaisesRegex(
                RuntimeError,
                "Example is not executable: /usr/bin/example",
            ),
        ):
            _require_executable(
                path,
                name="Example",
            )


class RunningAsRootTests(unittest.TestCase):
    def test_returns_true_for_root(self) -> None:
        with patch(
            f"{MODULE}.os.geteuid",
            return_value=0,
        ) as geteuid:
            result = running_as_root()

        self.assertTrue(result)
        geteuid.assert_called_once_with()

    def test_returns_false_for_non_root(self) -> None:
        with patch(
            f"{MODULE}.os.geteuid",
            return_value=1000,
        ):
            self.assertFalse(running_as_root())


class ElevateBetaboxTests(unittest.TestCase):
    def test_executes_expected_command(self) -> None:
        arguments = [
            "status",
            "--full",
        ]

        # os.execv normally never returns. Raising here lets the
        # test inspect the call without replacing the NoReturn
        # behavior with an unrealistic successful return.
        exec_error = OSError("test exec failure")

        with (
            patch(f"{MODULE}._require_executable") as require_executable,
            patch(
                f"{MODULE}.os.execv",
                side_effect=exec_error,
            ) as execv,
            self.assertRaisesRegex(
                RuntimeError,
                "Unable to elevate Betabox command",
            ) as context,
        ):
            elevate_betabox(arguments)

        self.assertIs(
            context.exception.__cause__,
            exec_error,
        )
        self.assertEqual(
            require_executable.call_args_list,
            [
                call(
                    BETABOX_EXECUTABLE,
                    name="Betabox executable",
                ),
                call(
                    SUDO_EXECUTABLE,
                    name="sudo",
                ),
            ],
        )
        execv.assert_called_once_with(
            str(SUDO_EXECUTABLE),
            [
                str(SUDO_EXECUTABLE),
                "-n",
                str(BETABOX_EXECUTABLE),
                "status",
                "--full",
            ],
        )

    def test_normalizes_arguments_before_exec(self) -> None:
        with (
            patch(f"{MODULE}._require_executable"),
            patch(
                f"{MODULE}.os.execv",
                side_effect=OSError("test"),
            ) as execv,
            self.assertRaises(RuntimeError),
        ):
            elevate_betabox(
                [
                    " status ",
                    " --full ",
                ]
            )

        execv.assert_called_once_with(
            str(SUDO_EXECUTABLE),
            [
                str(SUDO_EXECUTABLE),
                "-n",
                str(BETABOX_EXECUTABLE),
                "status",
                "--full",
            ],
        )

    def test_validates_arguments_before_executable_checks(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}._require_executable") as require_executable,
            self.assertRaisesRegex(
                TypeError,
                "arguments must be a list of strings",
            ),
        ):
            elevate_betabox(
                ("status",)  # type: ignore[arg-type]
            )

        require_executable.assert_not_called()

    def test_stops_when_betabox_executable_is_invalid(
        self,
    ) -> None:
        error = RuntimeError("Betabox executable is missing")

        with (
            patch(
                f"{MODULE}._require_executable",
                side_effect=error,
            ) as require_executable,
            patch(f"{MODULE}.os.execv") as execv,
            self.assertRaises(RuntimeError) as context,
        ):
            elevate_betabox(
                [
                    "status",
                ]
            )

        self.assertIs(
            context.exception,
            error,
        )
        require_executable.assert_called_once_with(
            BETABOX_EXECUTABLE,
            name="Betabox executable",
        )
        execv.assert_not_called()

    def test_stops_when_sudo_is_invalid(self) -> None:
        error = RuntimeError("sudo is missing")

        with (
            patch(
                f"{MODULE}._require_executable",
                side_effect=(
                    None,
                    error,
                ),
            ) as require_executable,
            patch(f"{MODULE}.os.execv") as execv,
            self.assertRaises(RuntimeError) as context,
        ):
            elevate_betabox(
                [
                    "status",
                ]
            )

        self.assertIs(
            context.exception,
            error,
        )
        self.assertEqual(
            require_executable.call_args_list,
            [
                call(
                    BETABOX_EXECUTABLE,
                    name="Betabox executable",
                ),
                call(
                    SUDO_EXECUTABLE,
                    name="sudo",
                ),
            ],
        )
        execv.assert_not_called()


class RequireRootOrElevateTests(unittest.TestCase):
    def test_root_process_continues_without_elevation(
        self,
    ) -> None:
        arguments = [
            "status",
        ]

        with (
            patch(
                f"{MODULE}.running_as_root",
                return_value=True,
            ) as is_root,
            patch(f"{MODULE}.elevate_betabox") as elevate,
        ):
            result = require_root_or_elevate(arguments)

        self.assertIsNone(result)
        is_root.assert_called_once_with()
        elevate.assert_not_called()

    def test_non_root_process_elevates(self) -> None:
        arguments = [
            "reset",
            "--yes",
        ]

        with (
            patch(
                f"{MODULE}.running_as_root",
                return_value=False,
            ),
            patch(f"{MODULE}.elevate_betabox") as elevate,
        ):
            require_root_or_elevate(arguments)

        elevate.assert_called_once_with(arguments)

    def test_non_root_propagates_elevation_failure(
        self,
    ) -> None:
        error = RuntimeError("sudo failed")

        with (
            patch(
                f"{MODULE}.running_as_root",
                return_value=False,
            ),
            patch(
                f"{MODULE}.elevate_betabox",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            require_root_or_elevate(
                [
                    "reset",
                ]
            )

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
