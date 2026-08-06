from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from betabox_robotics.services.install_checks.models import (
    CheckResult,
)
from betabox_robotics.services.install_checks.systemd import (
    AVAHI_OVERRIDE_REQUIRED_LINES,
    check_avahi_override,
    check_service_enabled,
    check_service_installed,
)

MODULE = "betabox_robotics.services.install_checks.systemd"


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


class CheckServiceInstalledTests(unittest.TestCase):
    def test_reports_installed_service(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            unit = "jupyterhub.service"
            path = root / unit

            path.write_text(
                "[Unit]\n",
                encoding="utf-8",
            )

            result = check_service_installed(
                unit,
                systemd_root=root,
            )

        self.assertEqual(
            result,
            CheckResult(
                name=("service-installed:jupyterhub.service"),
                ok=True,
                message="installed",
            ),
        )

    def test_reports_missing_service(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            result = check_service_installed(
                "missing.service",
                systemd_root=root,
            )

        self.assertEqual(
            result,
            CheckResult(
                name=("service-installed:missing.service"),
                ok=False,
                message="unit file missing",
            ),
        )

    def test_directory_is_not_installed_unit(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "directory.service"
            path.mkdir()

            result = check_service_installed(
                "directory.service",
                systemd_root=root,
            )

        self.assertFalse(result.ok)
        self.assertEqual(
            result.message,
            "unit file missing",
        )

    def test_strips_unit_and_accepts_string_root(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "service.service").write_text(
                "[Unit]\n",
                encoding="utf-8",
            )

            result = check_service_installed(
                " service.service ",
                systemd_root=temp_dir,
            )

        self.assertEqual(
            result.name,
            ("service-installed:service.service"),
        )
        self.assertTrue(result.ok)

    def test_checks_unit_file_once(self) -> None:
        root = Path("/etc/systemd/system")

        with patch.object(
            Path,
            "is_file",
            return_value=True,
        ) as is_file:
            result = check_service_installed(
                "service.service",
                systemd_root=root,
            )

        is_file.assert_called_once_with()
        self.assertTrue(result.ok)

    def test_reports_filesystem_error(self) -> None:
        with patch.object(
            Path,
            "is_file",
            side_effect=OSError("permission denied"),
        ):
            result = check_service_installed("service.service")

        self.assertEqual(
            result,
            CheckResult(
                name=("service-installed:service.service"),
                ok=False,
                message="permission denied",
            ),
        )

    def test_unexpected_filesystem_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch.object(
                Path,
                "is_file",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_service_installed("service.service")

        self.assertIs(
            context.exception,
            error,
        )

    def test_rejects_invalid_unit_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "is_file") as is_file,
            self.assertRaisesRegex(
                TypeError,
                "unit must be a string",
            ),
        ):
            check_service_installed(
                None  # type: ignore[arg-type]
            )

        is_file.assert_not_called()

    def test_rejects_empty_unit_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "is_file") as is_file,
            self.assertRaisesRegex(
                ValueError,
                "unit cannot be empty",
            ),
        ):
            check_service_installed(" ")

        is_file.assert_not_called()

    def test_rejects_invalid_root_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "is_file") as is_file,
            self.assertRaisesRegex(
                TypeError,
                ("systemd_root must be a string or Path"),
            ),
        ):
            check_service_installed(
                "service.service",
                systemd_root=True,  # type: ignore[arg-type]
            )

        is_file.assert_not_called()


class CheckServiceEnabledTests(unittest.TestCase):
    def test_reports_enabled_service(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout="enabled\n",
            ),
        ) as run:
            result = check_service_enabled(
                " service.service ",
                timeout=7,
            )

        run.assert_called_once_with(
            [
                "systemctl",
                "is-enabled",
                "service.service",
            ],
            timeout=7,
        )
        self.assertEqual(
            result,
            CheckResult(
                name=("service-enabled:service.service"),
                ok=True,
                message="enabled",
            ),
        )

    def test_reports_disabled_service(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=1,
                stdout="disabled\n",
            ),
        ):
            result = check_service_enabled("service.service")

        self.assertEqual(
            result,
            CheckResult(
                name=("service-enabled:service.service"),
                ok=False,
                message="disabled",
            ),
        )

    def test_reports_static_service(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=0,
                stdout="static\n",
            ),
        ):
            result = check_service_enabled("service.service")

        self.assertTrue(result.ok)
        self.assertEqual(
            result.message,
            "static",
        )

    def test_reports_masked_service(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=1,
                stdout="masked\n",
            ),
        ):
            result = check_service_enabled("service.service")

        self.assertFalse(result.ok)
        self.assertEqual(
            result.message,
            "masked",
        )

    def test_uses_stdout_before_stderr(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=1,
                stdout="disabled\n",
                stderr="error\n",
            ),
        ):
            result = check_service_enabled("service.service")

        self.assertEqual(
            result.message,
            "disabled",
        )

    def test_uses_stderr_when_stdout_empty(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=1,
                stderr="unit not found\n",
            ),
        ):
            result = check_service_enabled("service.service")

        self.assertFalse(result.ok)
        self.assertEqual(
            result.message,
            "unit not found",
        )

    def test_uses_unknown_for_empty_output(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=1,
            ),
        ):
            result = check_service_enabled("service.service")

        self.assertFalse(result.ok)
        self.assertEqual(
            result.message,
            "unknown",
        )

    def test_reports_command_failure(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=None,
        ):
            result = check_service_enabled("service.service")

        self.assertEqual(
            result,
            CheckResult(
                name=("service-enabled:service.service"),
                ok=False,
                message=("systemctl command failed"),
            ),
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
            check_service_enabled(
                None  # type: ignore[arg-type]
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
            check_service_enabled(" ")

        run.assert_not_called()

    def test_rejects_invalid_timeout_before_command(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            self.assertRaisesRegex(
                TypeError,
                "timeout must be an integer",
            ),
        ):
            check_service_enabled(
                "service.service",
                timeout=True,  # type: ignore[arg-type]
            )

        run.assert_not_called()

    def test_rejects_non_positive_timeout_before_command(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            self.assertRaisesRegex(
                ValueError,
                ("timeout must be greater than 0"),
            ),
        ):
            check_service_enabled(
                "service.service",
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
            check_service_enabled("service.service")

        self.assertIs(
            context.exception,
            error,
        )


class CheckAvahiOverrideTests(unittest.TestCase):
    def test_accepts_complete_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "override.conf"
            path.write_text(
                "\n".join(
                    (
                        "[Unit]",
                        *AVAHI_OVERRIDE_REQUIRED_LINES,
                    )
                ),
                encoding="utf-8",
            )

            result = check_avahi_override(path)

        self.assertEqual(
            result,
            CheckResult(
                name=("systemd-override:avahi-daemon"),
                ok=True,
                message=str(path),
            ),
        )

    def test_reports_missing_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "missing.conf"

            result = check_avahi_override(path)

        self.assertEqual(
            result,
            CheckResult(
                name=("systemd-override:avahi-daemon"),
                ok=False,
                message=f"{path} missing",
            ),
        )

    def test_reports_all_missing_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "override.conf"
            present_line = AVAHI_OVERRIDE_REQUIRED_LINES[0]
            path.write_text(
                (f"[Unit]\n{present_line}\n"),
                encoding="utf-8",
            )

            result = check_avahi_override(path)

        missing = AVAHI_OVERRIDE_REQUIRED_LINES[1:]

        self.assertFalse(result.ok)
        self.assertEqual(
            result.message,
            ("missing: " + ", ".join(missing)),
        )

    def test_reports_one_missing_line(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "override.conf"
            missing = AVAHI_OVERRIDE_REQUIRED_LINES[-1]
            present = AVAHI_OVERRIDE_REQUIRED_LINES[:-1]

            path.write_text(
                "\n".join(
                    (
                        "[Unit]",
                        *present,
                    )
                ),
                encoding="utf-8",
            )

            result = check_avahi_override(path)

        self.assertEqual(
            result.message,
            f"missing: {missing}",
        )

    def test_reads_with_utf8_and_ignored_errors(
        self,
    ) -> None:
        path = Path("/etc/systemd/system/avahi-daemon.service.d/override.conf")

        with (
            patch.object(
                Path,
                "is_file",
                return_value=True,
            ),
            patch.object(
                Path,
                "read_text",
                return_value="\n".join(AVAHI_OVERRIDE_REQUIRED_LINES),
            ) as read_text,
        ):
            result = check_avahi_override(path)

        read_text.assert_called_once_with(
            encoding="utf-8",
            errors="ignore",
        )
        self.assertTrue(result.ok)

    def test_reports_is_file_error(self) -> None:
        with patch.object(
            Path,
            "is_file",
            side_effect=OSError("permission denied"),
        ):
            result = check_avahi_override("/override.conf")

        self.assertEqual(
            result.message,
            "permission denied",
        )
        self.assertFalse(result.ok)

    def test_reports_read_error(self) -> None:
        with (
            patch.object(
                Path,
                "is_file",
                return_value=True,
            ),
            patch.object(
                Path,
                "read_text",
                side_effect=OSError("read failed"),
            ),
        ):
            result = check_avahi_override("/override.conf")

        self.assertEqual(
            result,
            CheckResult(
                name=("systemd-override:avahi-daemon"),
                ok=False,
                message="read failed",
            ),
        )

    def test_unexpected_read_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch.object(
                Path,
                "is_file",
                return_value=True,
            ),
            patch.object(
                Path,
                "read_text",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_avahi_override("/override.conf")

        self.assertIs(
            context.exception,
            error,
        )

    def test_rejects_invalid_path_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "is_file") as is_file,
            self.assertRaisesRegex(
                TypeError,
                "path must be a string or Path",
            ),
        ):
            check_avahi_override(
                True  # type: ignore[arg-type]
            )

        is_file.assert_not_called()


if __name__ == "__main__":
    unittest.main()
