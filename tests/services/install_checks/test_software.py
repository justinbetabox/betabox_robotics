from __future__ import annotations

import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.install_checks.models import (
    CheckResult,
)
from betabox_robotics.services.install_checks.software import (
    check_command,
    check_config_line,
    check_executable,
    check_import,
)

MODULE = "betabox_robotics.services.install_checks.software"


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


def make_config(
    boot_config_file: Path,
):
    verification = replace(
        DEFAULT_PLATFORM_CONFIG.verification,
        boot_config_file=boot_config_file,
    )

    return replace(
        DEFAULT_PLATFORM_CONFIG,
        verification=verification,
    )


class CheckImportTests(unittest.TestCase):
    def test_import_success_without_version(
        self,
    ) -> None:
        module = object()

        with patch(
            f"{MODULE}.importlib.import_module",
            return_value=module,
        ) as import_module:
            result = check_import(" json ")

        import_module.assert_called_once_with("json")
        self.assertEqual(
            result,
            CheckResult(
                name="import:json",
                ok=True,
                message="import ok",
            ),
        )

    def test_import_success_with_version(
        self,
    ) -> None:
        module = Mock()
        module.__version__ = "1.2.3"

        with patch(
            f"{MODULE}.importlib.import_module",
            return_value=module,
        ):
            result = check_import("example")

        self.assertEqual(
            result,
            CheckResult(
                name="import:example",
                ok=True,
                message="1.2.3",
            ),
        )

    def test_import_success_with_numeric_version(
        self,
    ) -> None:
        module = Mock()
        module.__version__ = 123

        with patch(
            f"{MODULE}.importlib.import_module",
            return_value=module,
        ):
            result = check_import("example")

        self.assertEqual(
            result.message,
            "123",
        )

    def test_import_success_with_none_version(
        self,
    ) -> None:
        module = Mock()
        module.__version__ = None

        with patch(
            f"{MODULE}.importlib.import_module",
            return_value=module,
        ):
            result = check_import("example")

        self.assertEqual(
            result.message,
            "import ok",
        )

    def test_import_success_with_empty_version(
        self,
    ) -> None:
        module = Mock()
        module.__version__ = "   "

        with patch(
            f"{MODULE}.importlib.import_module",
            return_value=module,
        ):
            result = check_import("example")

        self.assertEqual(
            result.message,
            "import ok",
        )

    def test_import_error_returns_failed_check(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.importlib.import_module",
            side_effect=ImportError("cannot import module"),
        ):
            result = check_import("broken")

        self.assertEqual(
            result,
            CheckResult(
                name="import:broken",
                ok=False,
                message="cannot import module",
            ),
        )

    def test_module_not_found_returns_failed_check(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.importlib.import_module",
            side_effect=ModuleNotFoundError("missing module"),
        ):
            result = check_import("missing")

        self.assertEqual(
            result,
            CheckResult(
                name="import:missing",
                ok=False,
                message="missing module",
            ),
        )

    def test_unexpected_import_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("module initialization failed")

        with (
            patch(
                f"{MODULE}.importlib.import_module",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_import("broken")

        self.assertIs(
            context.exception,
            error,
        )

    def test_rejects_invalid_module_before_import(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.importlib.import_module") as import_module,
            self.assertRaisesRegex(
                TypeError,
                "module must be a string",
            ),
        ):
            check_import(
                None  # type: ignore[arg-type]
            )

        import_module.assert_not_called()

    def test_rejects_empty_module_before_import(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.importlib.import_module") as import_module,
            self.assertRaisesRegex(
                ValueError,
                "module cannot be empty",
            ),
        ):
            check_import(" ")

        import_module.assert_not_called()


class CheckCommandTests(unittest.TestCase):
    def test_runs_command(self) -> None:
        result_value = make_result(stdout="help output\n")

        with patch(
            f"{MODULE}.run",
            return_value=result_value,
        ) as run:
            result = check_command(
                [
                    " betabox ",
                    " --help ",
                ],
                " cli:betabox ",
                timeout=7,
            )

        run.assert_called_once_with(
            [
                "betabox",
                "--help",
            ],
            timeout=7,
        )
        self.assertEqual(
            result,
            CheckResult(
                name="cli:betabox",
                ok=True,
                message="help output",
            ),
        )

    def test_success_uses_stdout(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout="success\n",
                stderr="warning\n",
            ),
        ):
            result = check_command(
                ["command"],
                "check",
            )

        self.assertTrue(result.ok)
        self.assertEqual(
            result.message,
            "success",
        )

    def test_failure_uses_stdout_before_stderr(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=1,
                stdout="stdout failure\n",
                stderr="stderr failure\n",
            ),
        ):
            result = check_command(
                ["command"],
                "check",
            )

        self.assertFalse(result.ok)
        self.assertEqual(
            result.message,
            "stdout failure",
        )

    def test_uses_stderr_when_stdout_empty(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=1,
                stderr="failed\n",
            ),
        ):
            result = check_command(
                ["command"],
                "check",
            )

        self.assertFalse(result.ok)
        self.assertEqual(
            result.message,
            "failed",
        )

    def test_success_without_output_uses_fallback(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(),
        ):
            result = check_command(
                ["command"],
                "check",
            )

        self.assertTrue(result.ok)
        self.assertEqual(
            result.message,
            "command succeeded",
        )

    def test_failure_without_output_uses_fallback(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(returncode=1),
        ):
            result = check_command(
                ["command"],
                "check",
            )

        self.assertFalse(result.ok)
        self.assertEqual(
            result.message,
            "command failed",
        )

    def test_command_cannot_run(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=None,
        ):
            result = check_command(
                ["command"],
                "check",
            )

        self.assertEqual(
            result,
            CheckResult(
                name="check",
                ok=False,
                message="command failed to run",
            ),
        )

    def test_nonzero_return_code_is_failure(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=2,
                stdout="usage error",
            ),
        ):
            result = check_command(
                ["command"],
                "check",
            )

        self.assertFalse(result.ok)

    def test_rejects_invalid_command_before_run(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            self.assertRaisesRegex(
                TypeError,
                ("command must be a sequence of strings"),
            ),
        ):
            check_command(
                "command",  # type: ignore[arg-type]
                "check",
            )

        run.assert_not_called()

    def test_rejects_empty_command_before_run(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            self.assertRaisesRegex(
                ValueError,
                "command cannot be empty",
            ),
        ):
            check_command(
                [],
                "check",
            )

        run.assert_not_called()

    def test_rejects_invalid_name_before_run(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            self.assertRaisesRegex(
                TypeError,
                "name must be a string",
            ),
        ):
            check_command(
                ["command"],
                None,  # type: ignore[arg-type]
            )

        run.assert_not_called()

    def test_rejects_empty_name_before_run(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            self.assertRaisesRegex(
                ValueError,
                "name cannot be empty",
            ),
        ):
            check_command(
                ["command"],
                " ",
            )

        run.assert_not_called()

    def test_rejects_invalid_timeout_before_run(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            self.assertRaisesRegex(
                TypeError,
                "timeout must be an integer",
            ),
        ):
            check_command(
                ["command"],
                "check",
                timeout=True,  # type: ignore[arg-type]
            )

        run.assert_not_called()

    def test_rejects_non_positive_timeout_before_run(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            self.assertRaisesRegex(
                ValueError,
                ("timeout must be greater than 0"),
            ),
        ):
            check_command(
                ["command"],
                "check",
                timeout=0,
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
            check_command(
                ["command"],
                "check",
            )

        self.assertIs(
            context.exception,
            error,
        )


class CheckConfigLineTests(unittest.TestCase):
    def test_reports_present_line(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.txt"
            config_file.write_text(
                ("dtparam=i2c_arm=on\ndtparam=spi=on\n"),
                encoding="utf-8",
            )
            config = make_config(config_file)

            result = check_config_line(
                "dtparam=i2c_arm=on",
                config,
            )

        self.assertEqual(
            result,
            CheckResult(
                name=("config:dtparam=i2c_arm=on"),
                ok=True,
                message="present",
            ),
        )

    def test_reports_missing_line(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.txt"
            config_file.write_text(
                "dtparam=spi=on\n",
                encoding="utf-8",
            )
            config = make_config(config_file)

            result = check_config_line(
                "dtparam=i2c_arm=on",
                config,
            )

        self.assertEqual(
            result,
            CheckResult(
                name=("config:dtparam=i2c_arm=on"),
                ok=False,
                message="missing",
            ),
        )

    def test_reports_missing_config_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "missing.txt"
            config = make_config(config_file)

            result = check_config_line(
                "dtparam=i2c_arm=on",
                config,
            )

        self.assertEqual(
            result,
            CheckResult(
                name=("config:dtparam=i2c_arm=on"),
                ok=False,
                message=(f"{config_file} missing"),
            ),
        )

    def test_strips_requested_line(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.txt"
            config_file.write_text(
                "dtparam=i2c_arm=on\n",
                encoding="utf-8",
            )
            config = make_config(config_file)

            result = check_config_line(
                " dtparam=i2c_arm=on ",
                config,
            )

        self.assertEqual(
            result.name,
            "config:dtparam=i2c_arm=on",
        )
        self.assertTrue(result.ok)

    def test_reads_with_utf8_and_ignored_errors(
        self,
    ) -> None:
        config_file = Path("/boot/firmware/config.txt")
        config = make_config(config_file)

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch.object(
                Path,
                "read_text",
                return_value=("dtparam=i2c_arm=on"),
            ) as read_text,
        ):
            result = check_config_line(
                "dtparam=i2c_arm=on",
                config,
            )

        read_text.assert_called_once_with(
            encoding="utf-8",
            errors="ignore",
        )
        self.assertTrue(result.ok)

    def test_reports_read_error(self) -> None:
        config_file = Path("/boot/firmware/config.txt")
        config = make_config(config_file)

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch.object(
                Path,
                "read_text",
                side_effect=OSError("permission denied"),
            ),
        ):
            result = check_config_line(
                "dtparam=i2c_arm=on",
                config,
            )

        self.assertEqual(
            result,
            CheckResult(
                name=("config:dtparam=i2c_arm=on"),
                ok=False,
                message="permission denied",
            ),
        )

    def test_unexpected_read_error_propagates(
        self,
    ) -> None:
        config_file = Path("/boot/firmware/config.txt")
        config = make_config(config_file)
        error = RuntimeError("programming error")

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch.object(
                Path,
                "read_text",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_config_line(
                "dtparam=i2c_arm=on",
                config,
            )

        self.assertIs(
            context.exception,
            error,
        )

    def test_rejects_invalid_line_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "exists") as exists,
            self.assertRaisesRegex(
                TypeError,
                "line must be a string",
            ),
        ):
            check_config_line(
                None  # type: ignore[arg-type]
            )

        exists.assert_not_called()

    def test_rejects_empty_line_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "exists") as exists,
            self.assertRaisesRegex(
                ValueError,
                "line cannot be empty",
            ),
        ):
            check_config_line(" ")

        exists.assert_not_called()

    def test_rejects_invalid_config_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "exists") as exists,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            check_config_line(
                "dtparam=i2c_arm=on",
                object(),  # type: ignore[arg-type]
            )

        exists.assert_not_called()


class CheckExecutableTests(unittest.TestCase):
    def test_reports_executable_path(self) -> None:
        with patch(
            f"{MODULE}.shutil.which",
            return_value="/usr/bin/python",
        ) as which:
            result = check_executable(" python ")

        which.assert_called_once_with("python")
        self.assertEqual(
            result,
            CheckResult(
                name="command:python",
                ok=True,
                message="/usr/bin/python",
            ),
        )

    def test_reports_missing_executable(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.shutil.which",
            return_value=None,
        ):
            result = check_executable("missing")

        self.assertEqual(
            result,
            CheckResult(
                name="command:missing",
                ok=False,
                message="not found",
            ),
        )

    def test_rejects_invalid_command_before_lookup(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.shutil.which") as which,
            self.assertRaisesRegex(
                TypeError,
                "command must be a string",
            ),
        ):
            check_executable(
                None  # type: ignore[arg-type]
            )

        which.assert_not_called()

    def test_rejects_empty_command_before_lookup(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.shutil.which") as which,
            self.assertRaisesRegex(
                ValueError,
                "command cannot be empty",
            ),
        ):
            check_executable(" ")

        which.assert_not_called()

    def test_unexpected_lookup_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.shutil.which",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_executable("python")

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
