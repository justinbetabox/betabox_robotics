from __future__ import annotations

import subprocess
import unittest
from unittest.mock import Mock, patch

from betabox_robotics.services.verify_checks.models import (
    CheckResult,
)
from betabox_robotics.services.verify_checks.software import (
    check_command,
    check_configurable_http_proxy,
    check_import,
    check_picamera2,
    check_speech_backend,
)

MODULE = "betabox_robotics.services.verify_checks.software"


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


class CheckImportTests(unittest.TestCase):
    def test_imports_module_without_version(
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

    def test_reports_module_version(self) -> None:
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

    def test_converts_numeric_version_to_string(
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

    def test_none_version_uses_import_ok(
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

    def test_blank_version_uses_import_ok(
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
    def test_runs_normalized_command(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(stdout="version output\n"),
        ) as run:
            result = check_command(
                [
                    " command ",
                    " --version ",
                ],
                " check:name ",
                timeout=7,
            )

        run.assert_called_once_with(
            [
                "command",
                "--version",
            ],
            timeout=7,
        )
        self.assertEqual(
            result,
            CheckResult(
                name="check:name",
                ok=True,
                message="version output",
            ),
        )

    def test_success_uses_stdout_before_stderr(
        self,
    ) -> None:
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

        self.assertEqual(
            result,
            CheckResult(
                name="check",
                ok=True,
                message="command succeeded",
            ),
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

        self.assertEqual(
            result,
            CheckResult(
                name="check",
                ok=False,
                message="command failed",
            ),
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


class CheckPicamera2Tests(unittest.TestCase):
    def test_reports_successful_import(self) -> None:
        imported = CheckResult(
            name="import:picamera2",
            ok=True,
            message="import ok",
        )

        with patch(
            f"{MODULE}.check_import",
            return_value=imported,
        ) as check_import:
            result = check_picamera2()

        check_import.assert_called_once_with("picamera2")
        self.assertEqual(
            result,
            CheckResult(
                name="camera:picamera2",
                ok=True,
                message="import ok",
            ),
        )

    def test_preserves_version_message(self) -> None:
        with patch(
            f"{MODULE}.check_import",
            return_value=CheckResult(
                name="import:picamera2",
                ok=True,
                message="0.3.30",
            ),
        ):
            result = check_picamera2()

        self.assertTrue(result.ok)
        self.assertEqual(
            result.message,
            "0.3.30",
        )

    def test_reports_failed_import(self) -> None:
        with patch(
            f"{MODULE}.check_import",
            return_value=CheckResult(
                name="import:picamera2",
                ok=False,
                message="module missing",
            ),
        ):
            result = check_picamera2()

        self.assertEqual(
            result,
            CheckResult(
                name="camera:picamera2",
                ok=False,
                message="module missing",
            ),
        )

    def test_unexpected_import_check_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.check_import",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_picamera2()

        self.assertIs(
            context.exception,
            error,
        )


class CheckConfigurableHttpProxyTests(unittest.TestCase):
    def test_reports_installed_proxy_version(
        self,
    ) -> None:
        command_result = CheckResult(
            name="jupyterhub:proxy",
            ok=True,
            message="5.0.0",
        )

        with patch(
            f"{MODULE}.check_command",
            return_value=command_result,
        ) as check_command:
            result = check_configurable_http_proxy(timeout=7)

        check_command.assert_called_once_with(
            [
                "configurable-http-proxy",
                "--version",
            ],
            "jupyterhub:proxy",
            timeout=7,
        )
        self.assertEqual(
            result,
            CheckResult(
                name="jupyterhub:proxy",
                ok=True,
                message="5.0.0",
            ),
        )

    def test_success_without_output_reports_installed(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.check_command",
            return_value=CheckResult(
                name="jupyterhub:proxy",
                ok=True,
                message="command succeeded",
            ),
        ):
            result = check_configurable_http_proxy()

        self.assertEqual(
            result.message,
            "installed",
        )

    def test_failed_command_reports_not_installed(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.check_command",
            return_value=CheckResult(
                name="jupyterhub:proxy",
                ok=False,
                message="command failed to run",
            ),
        ):
            result = check_configurable_http_proxy()

        self.assertEqual(
            result,
            CheckResult(
                name="jupyterhub:proxy",
                ok=False,
                message=("configurable-http-proxy not installed"),
            ),
        )

    def test_rejects_invalid_timeout_before_command(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.check_command") as check_command,
            self.assertRaisesRegex(
                TypeError,
                "timeout must be an integer",
            ),
        ):
            check_configurable_http_proxy(
                timeout=True,  # type: ignore[arg-type]
            )

        check_command.assert_not_called()

    def test_rejects_non_positive_timeout_before_command(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.check_command") as check_command,
            self.assertRaisesRegex(
                ValueError,
                ("timeout must be greater than 0"),
            ),
        ):
            check_configurable_http_proxy(timeout=0)

        check_command.assert_not_called()

    def test_unexpected_command_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.check_command",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_configurable_http_proxy()

        self.assertIs(
            context.exception,
            error,
        )


class CheckSpeechBackendTests(unittest.TestCase):
    def test_reports_available_backends(
        self,
    ) -> None:
        with patch(
            ("betabox_robotics.audio.speech.available_backends"),
            return_value=[
                " espeak-ng ",
                "pico2wave",
            ],
        ) as available_backends:
            result = check_speech_backend()

        available_backends.assert_called_once_with()
        self.assertEqual(
            result,
            CheckResult(
                name="audio:speech_backend",
                ok=True,
                message=("espeak-ng, pico2wave"),
            ),
        )

    def test_accepts_tuple_of_backends(
        self,
    ) -> None:
        with patch(
            ("betabox_robotics.audio.speech.available_backends"),
            return_value=("piper",),
        ):
            result = check_speech_backend()

        self.assertTrue(result.ok)
        self.assertEqual(
            result.message,
            "piper",
        )

    def test_reports_no_backends(self) -> None:
        with patch(
            ("betabox_robotics.audio.speech.available_backends"),
            return_value=[],
        ):
            result = check_speech_backend()

        self.assertEqual(
            result,
            CheckResult(
                name="audio:speech_backend",
                ok=False,
                message=("no speech backends found"),
            ),
        )

    def test_rejects_invalid_backend_value(
        self,
    ) -> None:
        with (
            patch(
                ("betabox_robotics.audio.speech.available_backends"),
                return_value=[
                    "espeak-ng",
                    123,
                ],
            ),
            self.assertRaisesRegex(
                TypeError,
                ("speech backend must be a string"),
            ),
        ):
            check_speech_backend()

    def test_rejects_empty_backend_value(
        self,
    ) -> None:
        with (
            patch(
                ("betabox_robotics.audio.speech.available_backends"),
                return_value=[
                    "espeak-ng",
                    " ",
                ],
            ),
            self.assertRaisesRegex(
                ValueError,
                ("speech backend cannot be empty"),
            ),
        ):
            check_speech_backend()

    def test_import_error_returns_failed_check(
        self,
    ) -> None:
        # Importing inside check_speech_backend makes a
        # direct import-failure test awkward. Simulate the
        # same expected exception from the backend call.
        with patch(
            ("betabox_robotics.audio.speech.available_backends"),
            side_effect=ImportError("speech module unavailable"),
        ):
            result = check_speech_backend()

        self.assertEqual(
            result,
            CheckResult(
                name="audio:speech_backend",
                ok=False,
                message=("speech module unavailable"),
            ),
        )

    def test_module_not_found_returns_failed_check(
        self,
    ) -> None:
        with patch(
            ("betabox_robotics.audio.speech.available_backends"),
            side_effect=ModuleNotFoundError("backend dependency missing"),
        ):
            result = check_speech_backend()

        self.assertEqual(
            result,
            CheckResult(
                name="audio:speech_backend",
                ok=False,
                message=("backend dependency missing"),
            ),
        )

    def test_unexpected_backend_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("backend detection failed")

        with (
            patch(
                ("betabox_robotics.audio.speech.available_backends"),
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_speech_backend()

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
