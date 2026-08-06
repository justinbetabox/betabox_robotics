from __future__ import annotations

import argparse
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.hostname import (
    _validate_config,
    _validate_flag,
    _validate_path,
    _validate_string,
    current_hostname,
    desired_hostname,
    main,
    parse_args,
    set_hostname,
    update_hosts_file,
)

MODULE = "betabox_robotics.services.hostname"


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
        result = _validate_string(
            " Betabox ",
            name="prefix",
        )

        self.assertEqual(
            result,
            "Betabox",
        )

    def test_validate_string_rejects_invalid_type(
        self,
    ) -> None:
        for value in (
            None,
            123,
            True,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "prefix must be a string",
                ),
            ):
                _validate_string(
                    value,
                    name="prefix",
                )

    def test_validate_string_rejects_empty_value(
        self,
    ) -> None:
        for value in (
            "",
            " ",
            "\t",
            "\n",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "prefix cannot be empty",
                ),
            ):
                _validate_string(
                    value,
                    name="prefix",
                )

    def test_validate_path_accepts_path(
        self,
    ) -> None:
        path = Path("/etc/hosts")

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
            "/etc/hosts",
            name="path",
        )

        self.assertEqual(
            result,
            Path("/etc/hosts"),
        )

    def test_validate_path_strips_string(
        self,
    ) -> None:
        result = _validate_path(
            " /etc/hosts ",
            name="path",
        )

        self.assertEqual(
            result,
            Path("/etc/hosts"),
        )

    def test_validate_path_expands_user(
        self,
    ) -> None:
        expanded = Path("/home/picar/hosts")

        with patch.object(
            Path,
            "expanduser",
            return_value=expanded,
        ) as expanduser:
            result = _validate_path(
                "~/hosts",
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
        for value in (
            None,
            123,
            object(),
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

    def test_validate_path_rejects_empty_string(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "path cannot be empty",
        ):
            _validate_path(
                " ",
                name="path",
            )

    def test_validate_flag_accepts_boolean(
        self,
    ) -> None:
        self.assertTrue(
            _validate_flag(
                True,
                name="dry_run",
            )
        )
        self.assertFalse(
            _validate_flag(
                False,
                name="dry_run",
            )
        )

    def test_validate_flag_rejects_non_boolean(
        self,
    ) -> None:
        for value in (
            None,
            0,
            1,
            "true",
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("dry_run must be a boolean"),
                ),
            ):
                _validate_flag(
                    value,
                    name="dry_run",
                )


class DesiredHostnameTests(unittest.TestCase):
    def test_returns_identity_name(self) -> None:
        with patch(
            f"{MODULE}.identity_name",
            return_value="Betabox-7eea",
        ) as identity_name:
            result = desired_hostname(" Betabox ")

        identity_name.assert_called_once_with("Betabox")
        self.assertEqual(
            result,
            "Betabox-7eea",
        )

    def test_returns_none_when_identity_unavailable(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.identity_name",
            return_value=None,
        ):
            result = desired_hostname("Betabox")

        self.assertIsNone(result)

    def test_rejects_invalid_prefix_before_lookup(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.identity_name") as identity_name,
            self.assertRaisesRegex(
                TypeError,
                "prefix must be a string",
            ),
        ):
            desired_hostname(
                None  # type: ignore[arg-type]
            )

        identity_name.assert_not_called()

    def test_rejects_empty_prefix_before_lookup(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.identity_name") as identity_name,
            self.assertRaisesRegex(
                ValueError,
                "prefix cannot be empty",
            ),
        ):
            desired_hostname(" ")

        identity_name.assert_not_called()

    def test_unexpected_identity_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("identity failed")

        with (
            patch(
                f"{MODULE}.identity_name",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            desired_hostname("Betabox")

        self.assertIs(
            context.exception,
            error,
        )


class CurrentHostnameTests(unittest.TestCase):
    def test_returns_hostname(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout="Betabox-7eea\n",
            ),
        ) as run:
            result = current_hostname()

        run.assert_called_once_with(
            [
                "hostname",
            ],
            timeout=5,
        )
        self.assertEqual(
            result,
            "Betabox-7eea",
        )

    def test_strips_hostname_output(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout="  Betabox-7eea  \n",
            ),
        ):
            result = current_hostname()

        self.assertEqual(
            result,
            "Betabox-7eea",
        )

    def test_reports_command_cannot_run(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.run",
                return_value=None,
            ),
            self.assertRaisesRegex(
                OSError,
                ("hostname command failed to run"),
            ),
        ):
            current_hostname()

    def test_failed_command_uses_stderr(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.run",
                return_value=make_result(
                    returncode=1,
                    stderr="hostname failed\n",
                ),
            ),
            self.assertRaisesRegex(
                OSError,
                "hostname failed",
            ),
        ):
            current_hostname()

    def test_failed_command_uses_stdout_fallback(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.run",
                return_value=make_result(
                    returncode=1,
                    stdout="failure output\n",
                ),
            ),
            self.assertRaisesRegex(
                OSError,
                "failure output",
            ),
        ):
            current_hostname()

    def test_failed_command_without_output(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.run",
                return_value=make_result(
                    returncode=1,
                ),
            ),
            self.assertRaisesRegex(
                OSError,
                "hostname command failed",
            ),
        ):
            current_hostname()

    def test_rejects_empty_hostname_output(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.run",
                return_value=make_result(),
            ),
            self.assertRaisesRegex(
                OSError,
                ("hostname command returned no hostname"),
            ),
        ):
            current_hostname()

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
            current_hostname()

        self.assertIs(
            context.exception,
            error,
        )


class UpdateHostsFileTests(unittest.TestCase):
    def test_replaces_existing_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "hosts"
            path.write_text(
                ("127.0.0.1\tlocalhost\n127.0.1.1\told-hostname\n::1\tlocalhost\n"),
                encoding="utf-8",
            )

            update_hosts_file(
                " Betabox-7eea ",
                path=path,
            )

            result = path.read_text(encoding="utf-8")

        self.assertEqual(
            result,
            ("127.0.0.1\tlocalhost\n127.0.1.1\tBetabox-7eea\n::1\tlocalhost\n"),
        )

    def test_appends_missing_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "hosts"
            path.write_text(
                "127.0.0.1\tlocalhost\n",
                encoding="utf-8",
            )

            update_hosts_file(
                "Betabox-7eea",
                path=path,
            )

            result = path.read_text(encoding="utf-8")

        self.assertEqual(
            result,
            ("127.0.0.1\tlocalhost\n127.0.1.1\tBetabox-7eea\n"),
        )

    def test_replaces_multiple_matching_entries(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "hosts"
            path.write_text(
                ("127.0.1.1\told-one\n127.0.1.1\told-two\n"),
                encoding="utf-8",
            )

            update_hosts_file(
                "Betabox-7eea",
                path=path,
            )

            result = path.read_text(encoding="utf-8")

        self.assertEqual(
            result,
            ("127.0.1.1\tBetabox-7eea\n127.0.1.1\tBetabox-7eea\n"),
        )

    def test_does_not_replace_similar_address(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "hosts"
            path.write_text(
                "127.0.1.10\tother-host\n",
                encoding="utf-8",
            )

            update_hosts_file(
                "Betabox-7eea",
                path=path,
            )

            result = path.read_text(encoding="utf-8")

        self.assertEqual(
            result,
            ("127.0.1.10\tother-host\n127.0.1.1\tBetabox-7eea\n"),
        )

    def test_dry_run_does_not_modify_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "hosts"
            original = "127.0.1.1\told-hostname\n"
            path.write_text(
                original,
                encoding="utf-8",
            )

            with patch("builtins.print") as print_message:
                update_hosts_file(
                    "Betabox-7eea",
                    dry_run=True,
                    path=path,
                )

            result = path.read_text(encoding="utf-8")

        self.assertEqual(
            result,
            original,
        )
        print_message.assert_called_once_with(
            f"Would update {path} 127.0.1.1 entry to Betabox-7eea"
        )

    def test_dry_run_does_not_read_file(
        self,
    ) -> None:
        path = Path("/etc/hosts")

        with (
            patch.object(Path, "read_text") as read_text,
            patch("builtins.print"),
        ):
            update_hosts_file(
                "Betabox-7eea",
                dry_run=True,
                path=path,
            )

        read_text.assert_not_called()

    def test_reads_and_writes_utf8(self) -> None:
        path = Path("/tmp/hosts")

        with (
            patch.object(
                Path,
                "read_text",
                return_value=("127.0.1.1\told\n"),
            ) as read_text,
            patch.object(Path, "write_text") as write_text,
        ):
            update_hosts_file(
                "Betabox-7eea",
                path=path,
            )

        read_text.assert_called_once_with(
            encoding="utf-8",
            errors="ignore",
        )
        write_text.assert_called_once_with(
            "127.0.1.1\tBetabox-7eea\n",
            encoding="utf-8",
        )

    def test_rejects_invalid_hostname_before_file_access(
        self,
    ) -> None:
        with (
            patch.object(Path, "read_text") as read_text,
            self.assertRaisesRegex(
                TypeError,
                "hostname must be a string",
            ),
        ):
            update_hosts_file(
                None,  # type: ignore[arg-type]
            )

        read_text.assert_not_called()

    def test_rejects_empty_hostname_before_file_access(
        self,
    ) -> None:
        with (
            patch.object(Path, "read_text") as read_text,
            self.assertRaisesRegex(
                ValueError,
                "hostname cannot be empty",
            ),
        ):
            update_hosts_file(" ")

        read_text.assert_not_called()

    def test_rejects_invalid_dry_run_before_file_access(
        self,
    ) -> None:
        with (
            patch.object(Path, "read_text") as read_text,
            self.assertRaisesRegex(
                TypeError,
                ("dry_run must be a boolean"),
            ),
        ):
            update_hosts_file(
                "Betabox-7eea",
                dry_run=1,  # type: ignore[arg-type]
            )

        read_text.assert_not_called()

    def test_rejects_invalid_path_before_file_access(
        self,
    ) -> None:
        with (
            patch.object(Path, "read_text") as read_text,
            self.assertRaisesRegex(
                TypeError,
                ("path must be a string or Path"),
            ),
        ):
            update_hosts_file(
                "Betabox-7eea",
                path=True,  # type: ignore[arg-type]
            )

        read_text.assert_not_called()

    def test_read_error_propagates(self) -> None:
        error = OSError("permission denied")

        with (
            patch.object(
                Path,
                "read_text",
                side_effect=error,
            ),
            self.assertRaises(OSError) as context,
        ):
            update_hosts_file("Betabox-7eea")

        self.assertIs(
            context.exception,
            error,
        )

    def test_write_error_propagates(self) -> None:
        error = OSError("write failed")

        with (
            patch.object(
                Path,
                "read_text",
                return_value="",
            ),
            patch.object(
                Path,
                "write_text",
                side_effect=error,
            ),
            self.assertRaises(OSError) as context,
        ):
            update_hosts_file("Betabox-7eea")

        self.assertIs(
            context.exception,
            error,
        )


class SetHostnameTests(unittest.TestCase):
    def test_uses_configured_prefix_by_default(
        self,
    ) -> None:
        expected_prefix = DEFAULT_PLATFORM_CONFIG.network.identity_prefix

        with (
            patch(
                f"{MODULE}.desired_hostname",
                return_value=None,
            ) as desired,
            patch(f"{MODULE}.current_hostname") as current,
            patch("builtins.print"),
        ):
            result = set_hostname()

        desired.assert_called_once_with(expected_prefix)
        current.assert_not_called()
        self.assertEqual(result, 0)

    def test_serial_unavailable_leaves_hostname_unchanged(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.desired_hostname",
                return_value=None,
            ),
            patch(f"{MODULE}.current_hostname") as current,
            patch(f"{MODULE}.run") as run,
            patch(f"{MODULE}.update_hosts_file") as update_hosts,
            patch("builtins.print") as print_message,
        ):
            result = set_hostname(prefix="Betabox")

        self.assertEqual(result, 0)
        current.assert_not_called()
        run.assert_not_called()
        update_hosts.assert_not_called()
        print_message.assert_called_once_with(
            "Could not determine serial; leaving hostname unchanged."
        )

    def test_already_correct_hostname(self) -> None:
        with (
            patch(
                f"{MODULE}.desired_hostname",
                return_value="Betabox-7eea",
            ),
            patch(
                f"{MODULE}.current_hostname",
                return_value="Betabox-7eea",
            ),
            patch(f"{MODULE}.run") as run,
            patch(f"{MODULE}.update_hosts_file") as update_hosts,
            patch("builtins.print") as print_message,
        ):
            result = set_hostname(prefix="Betabox")

        self.assertEqual(result, 0)
        run.assert_not_called()
        update_hosts.assert_not_called()
        print_message.assert_called_once_with("Hostname already correct: Betabox-7eea")

    def test_dry_run_prints_changes(self) -> None:
        with (
            patch(
                f"{MODULE}.desired_hostname",
                return_value="Betabox-7eea",
            ),
            patch(
                f"{MODULE}.current_hostname",
                return_value="raspberrypi",
            ),
            patch(f"{MODULE}.run") as run,
            patch(f"{MODULE}.update_hosts_file") as update_hosts,
            patch("builtins.print") as print_message,
        ):
            result = set_hostname(
                prefix="Betabox",
                dry_run=True,
            )

        self.assertEqual(result, 0)
        run.assert_not_called()
        update_hosts.assert_called_once_with(
            "Betabox-7eea",
            dry_run=True,
        )
        self.assertEqual(
            print_message.call_args_list,
            [
                call("Changing hostname from raspberrypi to Betabox-7eea"),
                call("Would run: hostnamectl set-hostname Betabox-7eea"),
            ],
        )

    def test_updates_hostname_and_hosts_file(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.desired_hostname",
                return_value="Betabox-7eea",
            ),
            patch(
                f"{MODULE}.current_hostname",
                return_value="raspberrypi",
            ),
            patch(
                f"{MODULE}.run",
                return_value=make_result(),
            ) as run,
            patch(f"{MODULE}.update_hosts_file") as update_hosts,
            patch("builtins.print") as print_message,
        ):
            result = set_hostname(
                prefix="Betabox",
            )

        self.assertEqual(result, 0)
        run.assert_called_once_with(
            [
                "hostnamectl",
                "set-hostname",
                "Betabox-7eea",
            ],
            timeout=5,
        )
        update_hosts.assert_called_once_with("Betabox-7eea")
        print_message.assert_called_once_with(
            "Changing hostname from raspberrypi to Betabox-7eea"
        )

    def test_hostnamectl_cannot_run(self) -> None:
        with (
            patch(
                f"{MODULE}.desired_hostname",
                return_value="Betabox-7eea",
            ),
            patch(
                f"{MODULE}.current_hostname",
                return_value="raspberrypi",
            ),
            patch(
                f"{MODULE}.run",
                return_value=None,
            ),
            patch(f"{MODULE}.update_hosts_file") as update_hosts,
            patch("builtins.print") as print_message,
        ):
            result = set_hostname(prefix="Betabox")

        self.assertEqual(result, 1)
        update_hosts.assert_not_called()
        self.assertEqual(
            print_message.call_args_list,
            [
                call("Changing hostname from raspberrypi to Betabox-7eea"),
                call("hostnamectl failed to run"),
            ],
        )

    def test_hostnamectl_failure_uses_stderr(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.desired_hostname",
                return_value="Betabox-7eea",
            ),
            patch(
                f"{MODULE}.current_hostname",
                return_value="raspberrypi",
            ),
            patch(
                f"{MODULE}.run",
                return_value=make_result(
                    returncode=4,
                    stderr="permission denied\n",
                ),
            ),
            patch(f"{MODULE}.update_hosts_file") as update_hosts,
            patch("builtins.print") as print_message,
        ):
            result = set_hostname(prefix="Betabox")

        self.assertEqual(result, 4)
        update_hosts.assert_not_called()
        self.assertEqual(
            print_message.call_args_list[-1],
            call("permission denied"),
        )

    def test_hostnamectl_failure_uses_stdout(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.desired_hostname",
                return_value="Betabox-7eea",
            ),
            patch(
                f"{MODULE}.current_hostname",
                return_value="raspberrypi",
            ),
            patch(
                f"{MODULE}.run",
                return_value=make_result(
                    returncode=2,
                    stdout="failed output\n",
                ),
            ),
            patch(f"{MODULE}.update_hosts_file"),
            patch("builtins.print") as print_message,
        ):
            result = set_hostname(prefix="Betabox")

        self.assertEqual(result, 2)
        self.assertEqual(
            print_message.call_args_list[-1],
            call("failed output"),
        )

    def test_hostnamectl_failure_without_output(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.desired_hostname",
                return_value="Betabox-7eea",
            ),
            patch(
                f"{MODULE}.current_hostname",
                return_value="raspberrypi",
            ),
            patch(
                f"{MODULE}.run",
                return_value=make_result(
                    returncode=3,
                ),
            ),
            patch(f"{MODULE}.update_hosts_file"),
            patch("builtins.print") as print_message,
        ):
            result = set_hostname(prefix="Betabox")

        self.assertEqual(result, 3)
        self.assertEqual(
            print_message.call_args_list[-1],
            call("hostnamectl failed"),
        )

    def test_negative_returncode_becomes_one(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.desired_hostname",
                return_value="Betabox-7eea",
            ),
            patch(
                f"{MODULE}.current_hostname",
                return_value="raspberrypi",
            ),
            patch(
                f"{MODULE}.run",
                return_value=make_result(
                    returncode=-9,
                ),
            ),
            patch(f"{MODULE}.update_hosts_file"),
            patch("builtins.print"),
        ):
            result = set_hostname(prefix="Betabox")

        self.assertEqual(result, 1)

    def test_rejects_invalid_config_before_identity(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.desired_hostname") as desired,
            self.assertRaisesRegex(
                TypeError,
                ("config must be a PlatformConfig"),
            ),
        ):
            set_hostname(
                config=object(),  # type: ignore[arg-type]
            )

        desired.assert_not_called()

    def test_rejects_invalid_dry_run_before_identity(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.desired_hostname") as desired,
            self.assertRaisesRegex(
                TypeError,
                ("dry_run must be a boolean"),
            ),
        ):
            set_hostname(
                dry_run=1,  # type: ignore[arg-type]
            )

        desired.assert_not_called()

    def test_rejects_invalid_prefix_before_identity(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.desired_hostname") as desired,
            self.assertRaisesRegex(
                TypeError,
                "prefix must be a string",
            ),
        ):
            set_hostname(
                prefix=123,  # type: ignore[arg-type]
            )

        desired.assert_not_called()

    def test_rejects_empty_prefix_before_identity(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.desired_hostname") as desired,
            self.assertRaisesRegex(
                ValueError,
                "prefix cannot be empty",
            ),
        ):
            set_hostname(prefix=" ")

        desired.assert_not_called()

    def test_rejects_empty_generated_hostname(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.desired_hostname",
                return_value=" ",
            ),
            patch(f"{MODULE}.current_hostname") as current,
            self.assertRaisesRegex(
                ValueError,
                "hostname cannot be empty",
            ),
        ):
            set_hostname(prefix="Betabox")

        current.assert_not_called()

    def test_current_hostname_error_propagates(
        self,
    ) -> None:
        error = OSError("hostname unavailable")

        with (
            patch(
                f"{MODULE}.desired_hostname",
                return_value="Betabox-7eea",
            ),
            patch(
                f"{MODULE}.current_hostname",
                side_effect=error,
            ),
            self.assertRaises(OSError) as context,
        ):
            set_hostname(prefix="Betabox")

        self.assertIs(
            context.exception,
            error,
        )

    def test_hosts_file_error_propagates(
        self,
    ) -> None:
        error = OSError("hosts update failed")

        with (
            patch(
                f"{MODULE}.desired_hostname",
                return_value="Betabox-7eea",
            ),
            patch(
                f"{MODULE}.current_hostname",
                return_value="raspberrypi",
            ),
            patch(
                f"{MODULE}.run",
                return_value=make_result(),
            ),
            patch(
                f"{MODULE}.update_hosts_file",
                side_effect=error,
            ),
            patch("builtins.print"),
            self.assertRaises(OSError) as context,
        ):
            set_hostname(prefix="Betabox")

        self.assertIs(
            context.exception,
            error,
        )


class ParseArgsTests(unittest.TestCase):
    def test_uses_configured_prefix_by_default(
        self,
    ) -> None:
        args = parse_args([])

        self.assertIsInstance(
            args,
            argparse.Namespace,
        )
        self.assertEqual(
            args.prefix,
            (DEFAULT_PLATFORM_CONFIG.network.identity_prefix),
        )
        self.assertFalse(args.dry_run)

    def test_parses_prefix(self) -> None:
        args = parse_args(
            [
                "--prefix",
                "Robot",
            ]
        )

        self.assertEqual(
            args.prefix,
            "Robot",
        )

    def test_parses_dry_run(self) -> None:
        args = parse_args(
            [
                "--dry-run",
            ]
        )

        self.assertTrue(args.dry_run)

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
    def test_calls_set_hostname(self) -> None:
        args = argparse.Namespace(
            prefix="Robot",
            dry_run=True,
        )

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=args,
            ) as parse,
            patch(
                f"{MODULE}.set_hostname",
                return_value=0,
            ) as set_hostname_call,
        ):
            result = main(
                [
                    "--prefix",
                    "Robot",
                    "--dry-run",
                ]
            )

        parse.assert_called_once_with(
            [
                "--prefix",
                "Robot",
                "--dry-run",
            ],
            config=DEFAULT_PLATFORM_CONFIG,
        )
        set_hostname_call.assert_called_once_with(
            prefix="Robot",
            dry_run=True,
            config=DEFAULT_PLATFORM_CONFIG,
        )
        self.assertEqual(result, 0)

    def test_preserves_nonzero_result(self) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(
                    prefix="Robot",
                    dry_run=False,
                ),
            ),
            patch(
                f"{MODULE}.set_hostname",
                return_value=4,
            ),
        ):
            result = main([])

        self.assertEqual(result, 4)

    def test_returns_one_for_type_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(
                    prefix="Robot",
                    dry_run=False,
                ),
            ),
            patch(
                f"{MODULE}.set_hostname",
                side_effect=TypeError("invalid prefix"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(result, 1)
        print_message.assert_called_once_with("invalid prefix")

    def test_returns_one_for_value_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(
                    prefix=" ",
                    dry_run=False,
                ),
            ),
            patch(
                f"{MODULE}.set_hostname",
                side_effect=ValueError("prefix cannot be empty"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(result, 1)
        print_message.assert_called_once_with("prefix cannot be empty")

    def test_returns_one_for_os_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(
                    prefix="Robot",
                    dry_run=False,
                ),
            ),
            patch(
                f"{MODULE}.set_hostname",
                side_effect=OSError("hostname unavailable"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(result, 1)
        print_message.assert_called_once_with("hostname unavailable")

    def test_unexpected_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(
                    prefix="Robot",
                    dry_run=False,
                ),
            ),
            patch(
                f"{MODULE}.set_hostname",
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
