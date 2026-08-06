from __future__ import annotations

import argparse
import subprocess
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import call, patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.logs import (
    LogTarget,
    _validate_config,
    _validate_flag,
    _validate_lines,
    _validate_path,
    _validate_string,
    get_target,
    journal_logs,
    log_targets,
    main,
    parse_args,
    print_target_logs,
    print_targets,
    tail_file,
)
from betabox_robotics.services.managed import (
    managed_services,
)

MODULE = "betabox_robotics.services.logs"

MANAGED_SERVICES = managed_services(DEFAULT_PLATFORM_CONFIG)
DEFAULT_MANAGED = next(iter(MANAGED_SERVICES.values()))


def make_result(
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def make_target(
    *,
    name: str = "launchpad",
    title: str = "Launchpad",
    unit: str | None = "betabox-launchpad.service",
    file: Path | None = Path("/var/log/betabox/launchpad.log"),
) -> LogTarget:
    return LogTarget(
        name=name,
        title=title,
        unit=unit,
        file=file,
    )


class ValidationTests(unittest.TestCase):
    def test_validate_config_accepts_config(
        self,
    ) -> None:
        result = _validate_config(DEFAULT_PLATFORM_CONFIG)

        self.assertIs(
            result,
            DEFAULT_PLATFORM_CONFIG,
        )

    def test_validate_config_rejects_invalid_value(
        self,
    ) -> None:
        for value in (
            None,
            object(),
            "config",
            123,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("config must be a PlatformConfig"),
                ),
            ):
                _validate_config(value)

    def test_validate_string_strips_value(
        self,
    ) -> None:
        self.assertEqual(
            _validate_string(
                " launchpad ",
                name="name",
            ),
            "launchpad",
        )

    def test_validate_string_rejects_invalid_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "name must be a string",
        ):
            _validate_string(
                None,
                name="name",
            )

    def test_validate_string_rejects_empty_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "name cannot be empty",
        ):
            _validate_string(
                " ",
                name="name",
            )

    def test_validate_path_accepts_path(
        self,
    ) -> None:
        path = Path("/var/log/test.log")

        result = _validate_path(
            path,
            name="path",
        )

        self.assertEqual(
            result,
            path,
        )

    def test_validate_path_accepts_string(
        self,
    ) -> None:
        result = _validate_path(
            "/var/log/test.log",
            name="path",
        )

        self.assertEqual(
            result,
            Path("/var/log/test.log"),
        )

    def test_validate_path_expands_user(
        self,
    ) -> None:
        expanded = Path("/home/picar/test.log")

        with patch.object(
            Path,
            "expanduser",
            return_value=expanded,
        ) as expanduser:
            result = _validate_path(
                "~/test.log",
                name="path",
            )

        expanduser.assert_called_once_with()
        self.assertEqual(
            result,
            expanded,
        )

    def test_validate_path_rejects_boolean(
        self,
    ) -> None:
        for value in (
            True,
            False,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("path must be a string or Path"),
                ),
            ):
                _validate_path(
                    value,
                    name="path",
                )

    def test_validate_path_rejects_invalid_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("path must be a string or Path"),
        ):
            _validate_path(
                object(),
                name="path",
            )

    def test_validate_lines_accepts_positive_integer(
        self,
    ) -> None:
        self.assertEqual(
            _validate_lines(50),
            50,
        )

    def test_validate_lines_rejects_boolean(
        self,
    ) -> None:
        for value in (
            True,
            False,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "lines must be an integer",
                ),
            ):
                _validate_lines(value)

    def test_validate_lines_rejects_invalid_type(
        self,
    ) -> None:
        for value in (
            None,
            1.5,
            "10",
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "lines must be an integer",
                ),
            ):
                _validate_lines(value)

    def test_validate_lines_rejects_non_positive_value(
        self,
    ) -> None:
        for value in (
            0,
            -1,
            -100,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    ("lines must be greater than 0"),
                ),
            ):
                _validate_lines(value)

    def test_validate_flag_accepts_boolean(
        self,
    ) -> None:
        self.assertTrue(
            _validate_flag(
                True,
                name="journal",
            )
        )
        self.assertFalse(
            _validate_flag(
                False,
                name="journal",
            )
        )

    def test_validate_flag_rejects_non_boolean(
        self,
    ) -> None:
        for value in (
            None,
            0,
            1,
            "yes",
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("journal must be a boolean"),
                ),
            ):
                _validate_flag(
                    value,
                    name="journal",
                )


class LogTargetTests(unittest.TestCase):
    def test_accepts_unit_and_file(self) -> None:
        target = make_target()

        self.assertEqual(
            target.name,
            "launchpad",
        )
        self.assertEqual(
            target.unit,
            "betabox-launchpad.service",
        )
        self.assertEqual(
            target.file,
            Path("/var/log/betabox/launchpad.log"),
        )

    def test_accepts_unit_only(self) -> None:
        target = make_target(file=None)

        self.assertIsNotNone(target.unit)
        self.assertIsNone(target.file)

    def test_accepts_file_only(self) -> None:
        target = make_target(unit=None)

        self.assertIsNone(target.unit)
        self.assertIsNotNone(target.file)

    def test_strips_string_fields(self) -> None:
        target = make_target(
            name=" launchpad ",
            title=" Launchpad ",
            unit=" service.service ",
        )

        self.assertEqual(
            target.name,
            "launchpad",
        )
        self.assertEqual(
            target.title,
            "Launchpad",
        )
        self.assertEqual(
            target.unit,
            "service.service",
        )

    def test_accepts_string_file(self) -> None:
        target = LogTarget(
            name="test",
            title="Test",
            unit=None,
            file="/var/log/test.log",  # type: ignore[arg-type]
        )

        self.assertEqual(
            target.file,
            Path("/var/log/test.log"),
        )

    def test_rejects_missing_unit_and_file(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            ("target must define a unit or file"),
        ):
            make_target(
                unit=None,
                file=None,
            )

    def test_rejects_invalid_name(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "name must be a string",
        ):
            make_target(
                name=None,  # type: ignore[arg-type]
            )

    def test_rejects_empty_title(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "title cannot be empty",
        ):
            make_target(title=" ")

    def test_rejects_invalid_unit(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "unit must be a string",
        ):
            make_target(
                unit=123,  # type: ignore[arg-type]
            )

    def test_rejects_invalid_file(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("file must be a string or Path"),
        ):
            make_target(
                file=True,  # type: ignore[arg-type]
            )

    def test_is_frozen(self) -> None:
        target = make_target()

        with self.assertRaises(FrozenInstanceError):
            target.name = "changed"  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        target = make_target()

        self.assertFalse(
            hasattr(
                target,
                "__dict__",
            )
        )


class GetTargetTests(unittest.TestCase):
    def test_returns_managed_target(self) -> None:
        with patch(
            f"{MODULE}.managed_services",
            return_value={
                DEFAULT_MANAGED.name: (DEFAULT_MANAGED),
            },
        ) as get_managed:
            result = get_target(
                f" {DEFAULT_MANAGED.name} ",
                DEFAULT_PLATFORM_CONFIG,
            )

        get_managed.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        self.assertIsNotNone(result)

        assert result is not None

        self.assertEqual(
            result.name,
            DEFAULT_MANAGED.name,
        )
        self.assertEqual(
            result.title,
            DEFAULT_MANAGED.title,
        )
        self.assertEqual(
            result.unit,
            DEFAULT_MANAGED.unit,
        )
        self.assertEqual(
            result.file,
            DEFAULT_MANAGED.log_file,
        )

    def test_returns_none_for_unknown_target(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.managed_services",
            return_value={},
        ):
            result = get_target("missing")

        self.assertIsNone(result)

    def test_rejects_invalid_name_before_lookup(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.managed_services") as get_managed,
            self.assertRaisesRegex(
                TypeError,
                "name must be a string",
            ),
        ):
            get_target(
                None  # type: ignore[arg-type]
            )

        get_managed.assert_not_called()

    def test_rejects_empty_name_before_lookup(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.managed_services") as get_managed,
            self.assertRaisesRegex(
                ValueError,
                "name cannot be empty",
            ),
        ):
            get_target(" ")

        get_managed.assert_not_called()

    def test_rejects_invalid_config_before_lookup(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.managed_services") as get_managed,
            self.assertRaisesRegex(
                TypeError,
                ("config must be a PlatformConfig"),
            ),
        ):
            get_target(
                "launchpad",
                object(),  # type: ignore[arg-type]
            )

        get_managed.assert_not_called()

    def test_lookup_error_propagates(self) -> None:
        error = RuntimeError("registry failed")

        with (
            patch(
                f"{MODULE}.managed_services",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            get_target("launchpad")

        self.assertIs(
            context.exception,
            error,
        )


class TailFileTests(unittest.TestCase):
    def test_returns_log_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "test.log"
            path.write_text(
                "content",
                encoding="utf-8",
            )

            with patch(
                f"{MODULE}.run",
                return_value=make_result(
                    stdout="line one\nline two\n",
                ),
            ) as run:
                result = tail_file(
                    path,
                    25,
                )

        run.assert_called_once_with(
            [
                "tail",
                "-n",
                "25",
                str(path),
            ],
            timeout=10,
        )
        self.assertEqual(
            result,
            "line one\nline two",
        )

    def test_returns_empty_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "test.log"
            path.touch()

            with patch(
                f"{MODULE}.run",
                return_value=make_result(),
            ):
                result = tail_file(
                    path,
                    10,
                )

        self.assertEqual(
            result,
            "(empty)",
        )

    def test_reports_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "missing.log"

            with patch(f"{MODULE}.run") as run:
                result = tail_file(
                    path,
                    10,
                )

        self.assertEqual(
            result,
            f"Log file not found: {path}",
        )
        run.assert_not_called()

    def test_reports_exists_error(self) -> None:
        path = Path("/var/log/test.log")

        with patch.object(
            Path,
            "exists",
            side_effect=OSError("permission denied"),
        ):
            result = tail_file(
                path,
                10,
            )

        self.assertEqual(
            result,
            (f"Could not read log file: {path}: permission denied"),
        )

    def test_returns_command_failure_message(
        self,
    ) -> None:
        path = Path("/var/log/test.log")

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
            result = tail_file(
                path,
                10,
            )

        self.assertEqual(
            result,
            (f"Could not read log file: {path}"),
        )

    def test_nonzero_command_uses_stderr(
        self,
    ) -> None:
        path = Path("/var/log/test.log")

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch(
                f"{MODULE}.run",
                return_value=make_result(
                    returncode=1,
                    stderr="read failed\n",
                ),
            ),
        ):
            result = tail_file(
                path,
                10,
            )

        self.assertEqual(
            result,
            "read failed",
        )

    def test_nonzero_command_uses_stdout_fallback(
        self,
    ) -> None:
        path = Path("/var/log/test.log")

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch(
                f"{MODULE}.run",
                return_value=make_result(
                    returncode=1,
                    stdout="tail failed\n",
                ),
            ),
        ):
            result = tail_file(
                path,
                10,
            )

        self.assertEqual(
            result,
            "tail failed",
        )

    def test_nonzero_command_without_output(
        self,
    ) -> None:
        path = Path("/var/log/test.log")

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch(
                f"{MODULE}.run",
                return_value=make_result(returncode=1),
            ),
        ):
            result = tail_file(
                path,
                10,
            )

        self.assertEqual(
            result,
            (f"Could not read log file: {path}"),
        )

    def test_accepts_string_path(self) -> None:
        path = Path("/var/log/test.log")

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch(
                f"{MODULE}.run",
                return_value=make_result(stdout="output"),
            ),
        ):
            result = tail_file(
                str(path),
                10,
            )

        self.assertEqual(
            result,
            "output",
        )

    def test_rejects_invalid_path_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "exists") as exists,
            self.assertRaisesRegex(
                TypeError,
                ("path must be a string or Path"),
            ),
        ):
            tail_file(
                True,  # type: ignore[arg-type]
                10,
            )

        exists.assert_not_called()

    def test_rejects_invalid_lines_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "exists") as exists,
            self.assertRaisesRegex(
                ValueError,
                ("lines must be greater than 0"),
            ),
        ):
            tail_file(
                "/var/log/test.log",
                0,
            )

        exists.assert_not_called()

    def test_unexpected_filesystem_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch.object(
                Path,
                "exists",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            tail_file(
                "/var/log/test.log",
                10,
            )

        self.assertIs(
            context.exception,
            error,
        )


class JournalLogsTests(unittest.TestCase):
    def test_returns_journal_output(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout="journal output\n",
            ),
        ) as run:
            result = journal_logs(
                " service.service ",
                50,
            )

        run.assert_called_once_with(
            [
                "journalctl",
                "-u",
                "service.service",
                "-n",
                "50",
                "--no-pager",
            ],
            timeout=10,
        )
        self.assertEqual(
            result,
            "journal output",
        )

    def test_uses_stderr_when_stdout_empty(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stderr="warning output\n",
            ),
        ):
            result = journal_logs(
                "service.service",
                10,
            )

        self.assertEqual(
            result,
            "warning output",
        )

    def test_returns_no_entries_marker(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(),
        ):
            result = journal_logs(
                "service.service",
                10,
            )

        self.assertEqual(
            result,
            "(no journal entries)",
        )

    def test_reports_command_failure(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=None,
        ):
            result = journal_logs(
                "service.service",
                10,
            )

        self.assertEqual(
            result,
            ("Could not read journal for service.service"),
        )

    def test_nonzero_command_uses_output(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=1,
                stderr="journal failed\n",
            ),
        ):
            result = journal_logs(
                "service.service",
                10,
            )

        self.assertEqual(
            result,
            "journal failed",
        )

    def test_nonzero_command_without_output(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(returncode=1),
        ):
            result = journal_logs(
                "service.service",
                10,
            )

        self.assertEqual(
            result,
            ("Could not read journal for service.service"),
        )

    def test_rejects_invalid_unit_before_command(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            self.assertRaisesRegex(
                TypeError,
                "unit must be a string",
            ),
        ):
            journal_logs(
                None,  # type: ignore[arg-type]
                10,
            )

        run.assert_not_called()

    def test_rejects_empty_unit_before_command(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            self.assertRaisesRegex(
                ValueError,
                "unit cannot be empty",
            ),
        ):
            journal_logs(
                " ",
                10,
            )

        run.assert_not_called()

    def test_rejects_invalid_lines_before_command(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            self.assertRaisesRegex(
                TypeError,
                "lines must be an integer",
            ),
        ):
            journal_logs(
                "service.service",
                True,  # type: ignore[arg-type]
            )

        run.assert_not_called()

    def test_unexpected_runner_error_propagates(
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
            journal_logs(
                "service.service",
                10,
            )

        self.assertIs(
            context.exception,
            error,
        )


class PrintTargetLogsTests(unittest.TestCase):
    def test_prints_file_and_journal_logs(
        self,
    ) -> None:
        target = make_target()

        with (
            patch(
                f"{MODULE}.tail_file",
                return_value="file output",
            ) as tail,
            patch(
                f"{MODULE}.journal_logs",
                return_value="journal output",
            ) as journal,
            patch("builtins.print") as print_message,
        ):
            print_target_logs(
                target,
                lines=25,
                journal=True,
                file=True,
            )

        tail.assert_called_once_with(
            target.file,
            25,
        )
        journal.assert_called_once_with(
            target.unit,
            25,
        )
        self.assertEqual(
            print_message.call_args_list,
            [
                call(),
                call("Betabox Logs: Launchpad"),
                call("=" * (14 + len("Launchpad"))),
                call(),
                call("File Log"),
                call("--------"),
                call("file output"),
                call(),
                call("Systemd Journal"),
                call("---------------"),
                call("journal output"),
                call(),
            ],
        )

    def test_prints_file_only(self) -> None:
        target = make_target()

        with (
            patch(
                f"{MODULE}.tail_file",
                return_value="file output",
            ) as tail,
            patch(f"{MODULE}.journal_logs") as journal,
            patch("builtins.print"),
        ):
            print_target_logs(
                target,
                lines=10,
                journal=False,
                file=True,
            )

        tail.assert_called_once_with(
            target.file,
            10,
        )
        journal.assert_not_called()

    def test_prints_journal_only(self) -> None:
        target = make_target()

        with (
            patch(f"{MODULE}.tail_file") as tail,
            patch(
                f"{MODULE}.journal_logs",
                return_value="journal output",
            ) as journal,
            patch("builtins.print"),
        ):
            print_target_logs(
                target,
                lines=10,
                journal=True,
                file=False,
            )

        tail.assert_not_called()
        journal.assert_called_once_with(
            target.unit,
            10,
        )

    def test_skips_missing_file_source(self) -> None:
        target = make_target(file=None)

        with (
            patch(f"{MODULE}.tail_file") as tail,
            patch(
                f"{MODULE}.journal_logs",
                return_value="journal output",
            ) as journal,
            patch("builtins.print"),
        ):
            print_target_logs(
                target,
                lines=10,
                journal=True,
                file=True,
            )

        tail.assert_not_called()
        journal.assert_called_once_with(
            target.unit,
            10,
        )

    def test_skips_missing_journal_source(
        self,
    ) -> None:
        target = make_target(unit=None)

        with (
            patch(
                f"{MODULE}.tail_file",
                return_value="file output",
            ) as tail,
            patch(f"{MODULE}.journal_logs") as journal,
            patch("builtins.print"),
        ):
            print_target_logs(
                target,
                lines=10,
                journal=True,
                file=True,
            )

        tail.assert_called_once_with(
            target.file,
            10,
        )
        journal.assert_not_called()

    def test_rejects_invalid_target_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                ("target must be a LogTarget"),
            ),
        ):
            print_target_logs(
                object(),  # type: ignore[arg-type]
                lines=10,
                journal=True,
                file=True,
            )

        print_message.assert_not_called()

    def test_rejects_invalid_lines_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                ValueError,
                ("lines must be greater than 0"),
            ),
        ):
            print_target_logs(
                make_target(),
                lines=0,
                journal=True,
                file=True,
            )

        print_message.assert_not_called()

    def test_rejects_invalid_journal_flag(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                ("journal must be a boolean"),
            ),
        ):
            print_target_logs(
                make_target(),
                lines=10,
                journal=1,  # type: ignore[arg-type]
                file=True,
            )

        print_message.assert_not_called()

    def test_rejects_invalid_file_flag(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                "file must be a boolean",
            ),
        ):
            print_target_logs(
                make_target(),
                lines=10,
                journal=True,
                file=1,  # type: ignore[arg-type]
            )

        print_message.assert_not_called()

    def test_rejects_both_outputs_disabled(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                ValueError,
                ("journal or file output must be enabled"),
            ),
        ):
            print_target_logs(
                make_target(),
                lines=10,
                journal=False,
                file=False,
            )

        print_message.assert_not_called()

    def test_output_error_propagates(self) -> None:
        error = RuntimeError("tail failed unexpectedly")

        with (
            patch(
                f"{MODULE}.tail_file",
                side_effect=error,
            ),
            patch("builtins.print"),
            self.assertRaises(RuntimeError) as context,
        ):
            print_target_logs(
                make_target(),
                lines=10,
                journal=False,
                file=True,
            )

        self.assertIs(
            context.exception,
            error,
        )


class LogTargetsTests(unittest.TestCase):
    def test_returns_all_managed_targets_in_order(
        self,
    ) -> None:
        managed = managed_services(DEFAULT_PLATFORM_CONFIG)

        with patch(
            f"{MODULE}.managed_services",
            return_value=managed,
        ) as get_managed:
            result = log_targets(DEFAULT_PLATFORM_CONFIG)

        self.assertIsInstance(
            result,
            tuple,
        )
        self.assertEqual(
            len(result),
            len(managed),
        )
        self.assertEqual(
            tuple(target.name for target in result),
            tuple(service.name for service in managed.values()),
        )
        get_managed.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)

    def test_accepts_empty_registry(self) -> None:
        with patch(
            f"{MODULE}.managed_services",
            return_value={},
        ):
            result = log_targets()

        self.assertEqual(
            result,
            (),
        )

    def test_rejects_invalid_config_before_lookup(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.managed_services") as get_managed,
            self.assertRaisesRegex(
                TypeError,
                ("config must be a PlatformConfig"),
            ),
        ):
            log_targets(
                object()  # type: ignore[arg-type]
            )

        get_managed.assert_not_called()

    def test_registry_error_propagates(self) -> None:
        error = RuntimeError("registry failed")

        with (
            patch(
                f"{MODULE}.managed_services",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            log_targets()

        self.assertIs(
            context.exception,
            error,
        )


class PrintTargetsTests(unittest.TestCase):
    def test_prints_targets(self) -> None:
        targets = (
            make_target(),
            make_target(
                name="monitor",
                title="Monitor",
                unit="betabox-monitor.service",
                file=None,
            ),
        )

        with patch("builtins.print") as print_message:
            print_targets(targets)

        self.assertEqual(
            print_message.call_args_list,
            [
                call(),
                call("Available log targets"),
                call("====================="),
                call(),
                call(f"{'launchpad':14} Launchpad"),
                call(f"{'monitor':14} Monitor"),
                call(),
            ],
        )

    def test_prints_empty_target_list(self) -> None:
        with patch("builtins.print") as print_message:
            print_targets(())

        self.assertEqual(
            print_message.call_args_list,
            [
                call(),
                call("Available log targets"),
                call("====================="),
                call(),
                call(),
            ],
        )

    def test_rejects_non_tuple_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                "targets must be a tuple",
            ),
        ):
            print_targets(
                []  # type: ignore[arg-type]
            )

        print_message.assert_not_called()

    def test_rejects_invalid_target_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                ("targets must contain only LogTarget values"),
            ),
        ):
            print_targets(
                (
                    object(),  # type: ignore[arg-type]
                )
            )

        print_message.assert_not_called()


class ParseArgsTests(unittest.TestCase):
    def test_defaults(self) -> None:
        args = parse_args([])

        self.assertIsInstance(
            args,
            argparse.Namespace,
        )
        self.assertIsNone(args.target)
        self.assertEqual(
            args.lines,
            (DEFAULT_PLATFORM_CONFIG.monitoring.default_log_lines),
        )
        self.assertFalse(args.journal_only)
        self.assertFalse(args.file_only)
        self.assertFalse(args.list)

    def test_parses_all_options(self) -> None:
        args = parse_args(
            [
                "launchpad",
                "--lines",
                "25",
                "--journal-only",
                "--list",
            ]
        )

        self.assertEqual(
            args.target,
            "launchpad",
        )
        self.assertEqual(
            args.lines,
            25,
        )
        self.assertTrue(args.journal_only)
        self.assertFalse(args.file_only)
        self.assertTrue(args.list)

    def test_parses_short_lines_option(
        self,
    ) -> None:
        args = parse_args(
            [
                "launchpad",
                "-n",
                "40",
            ]
        )

        self.assertEqual(
            args.lines,
            40,
        )

    def test_rejects_invalid_lines_argument(
        self,
    ) -> None:
        with (
            patch("sys.stderr"),
            self.assertRaises(SystemExit),
        ):
            parse_args(
                [
                    "--lines",
                    "invalid",
                ]
            )

    def test_rejects_unknown_argument(self) -> None:
        with (
            patch("sys.stderr"),
            self.assertRaises(SystemExit),
        ):
            parse_args(
                [
                    "--unknown",
                ]
            )

    def test_rejects_invalid_config_before_parser(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("config must be a PlatformConfig"),
        ):
            parse_args(
                [],
                config=object(),  # type: ignore[arg-type]
            )


class MainTests(unittest.TestCase):
    def make_args(
        self,
        *,
        target: str | None = "launchpad",
        lines: object = 50,
        journal_only: bool = False,
        file_only: bool = False,
        list_value: bool = False,
    ) -> argparse.Namespace:
        return argparse.Namespace(
            target=target,
            lines=lines,
            journal_only=journal_only,
            file_only=file_only,
            list=list_value,
        )

    def test_lists_targets_when_requested(
        self,
    ) -> None:
        targets = (make_target(),)

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(list_value=True),
            ) as parse,
            patch(
                f"{MODULE}.log_targets",
                return_value=targets,
            ) as collect_targets,
            patch(f"{MODULE}.print_targets") as print_targets_call,
            patch(f"{MODULE}.get_target") as get_target_call,
        ):
            result = main(
                [
                    "--list",
                ]
            )

        self.assertEqual(
            result,
            0,
        )
        parse.assert_called_once_with(
            [
                "--list",
            ],
            config=DEFAULT_PLATFORM_CONFIG,
        )
        collect_targets.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        print_targets_call.assert_called_once_with(targets)
        get_target_call.assert_not_called()

    def test_lists_targets_without_target(
        self,
    ) -> None:
        targets = (make_target(),)

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(target=None),
            ),
            patch(
                f"{MODULE}.log_targets",
                return_value=targets,
            ),
            patch(f"{MODULE}.print_targets") as print_targets_call,
        ):
            result = main([])

        self.assertEqual(
            result,
            0,
        )
        print_targets_call.assert_called_once_with(targets)

    def test_prints_selected_target_logs(
        self,
    ) -> None:
        target = make_target()
        targets = (target,)

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(lines=25),
            ),
            patch(
                f"{MODULE}.log_targets",
                return_value=targets,
            ),
            patch(
                f"{MODULE}.get_target",
                return_value=target,
            ) as get_target_call,
            patch(f"{MODULE}.print_target_logs") as print_logs,
        ):
            result = main(
                [
                    "launchpad",
                    "--lines",
                    "25",
                ]
            )

        self.assertEqual(
            result,
            0,
        )
        get_target_call.assert_called_once_with(
            "launchpad",
            DEFAULT_PLATFORM_CONFIG,
        )
        print_logs.assert_called_once_with(
            target,
            lines=25,
            journal=True,
            file=True,
        )

    def test_journal_only(self) -> None:
        target = make_target()

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(journal_only=True),
            ),
            patch(
                f"{MODULE}.log_targets",
                return_value=(target,),
            ),
            patch(
                f"{MODULE}.get_target",
                return_value=target,
            ),
            patch(f"{MODULE}.print_target_logs") as print_logs,
        ):
            result = main([])

        self.assertEqual(
            result,
            0,
        )
        print_logs.assert_called_once_with(
            target,
            lines=50,
            journal=True,
            file=False,
        )

    def test_file_only(self) -> None:
        target = make_target()

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(file_only=True),
            ),
            patch(
                f"{MODULE}.log_targets",
                return_value=(target,),
            ),
            patch(
                f"{MODULE}.get_target",
                return_value=target,
            ),
            patch(f"{MODULE}.print_target_logs") as print_logs,
        ):
            result = main([])

        self.assertEqual(
            result,
            0,
        )
        print_logs.assert_called_once_with(
            target,
            lines=50,
            journal=False,
            file=True,
        )

    def test_rejects_invalid_lines(self) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(lines=0),
            ),
            patch(f"{MODULE}.log_targets") as collect_targets,
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once_with("lines must be greater than 0")
        collect_targets.assert_not_called()

    def test_rejects_conflicting_output_flags(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(
                    journal_only=True,
                    file_only=True,
                ),
            ),
            patch(f"{MODULE}.log_targets") as collect_targets,
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once_with(
            "--journal-only and --file-only cannot be used together"
        )
        collect_targets.assert_not_called()

    def test_reports_unknown_target(self) -> None:
        targets = (make_target(),)

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(target="missing"),
            ),
            patch(
                f"{MODULE}.log_targets",
                return_value=targets,
            ),
            patch(
                f"{MODULE}.get_target",
                return_value=None,
            ),
            patch(f"{MODULE}.print_targets") as print_targets_call,
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(
            result,
            1,
        )
        self.assertEqual(
            print_message.call_args_list,
            [
                call("Unknown log target: missing"),
            ],
        )
        print_targets_call.assert_called_once_with(targets)

    def test_returns_one_for_target_validation_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(),
            ),
            patch(
                f"{MODULE}.log_targets",
                return_value=(),
            ),
            patch(
                f"{MODULE}.get_target",
                side_effect=ValueError("name cannot be empty"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once_with("name cannot be empty")

    def test_returns_one_for_target_collection_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(),
            ),
            patch(
                f"{MODULE}.log_targets",
                side_effect=OSError("registry unavailable"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once_with("registry unavailable")

    def test_returns_one_for_log_output_error(
        self,
    ) -> None:
        target = make_target()

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(),
            ),
            patch(
                f"{MODULE}.log_targets",
                return_value=(target,),
            ),
            patch(
                f"{MODULE}.get_target",
                return_value=target,
            ),
            patch(
                f"{MODULE}.print_target_logs",
                side_effect=OSError("log unavailable"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once_with("log unavailable")

    def test_unexpected_collection_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(),
            ),
            patch(
                f"{MODULE}.log_targets",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            main([])

        self.assertIs(
            context.exception,
            error,
        )

    def test_unexpected_output_error_propagates(
        self,
    ) -> None:
        target = make_target()
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(),
            ),
            patch(
                f"{MODULE}.log_targets",
                return_value=(target,),
            ),
            patch(
                f"{MODULE}.get_target",
                return_value=target,
            ),
            patch(
                f"{MODULE}.print_target_logs",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            main([])

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
