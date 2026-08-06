from __future__ import annotations

import argparse
import json
import subprocess
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, patch

from betabox_robotics.config import DEFAULT_PLATFORM_CONFIG
from betabox_robotics.services.snapshot import (
    SYSTEM_COMMANDS,
    SnapshotReport,
    _build_parser,
    _validate_command,
    _validate_config,
    _validate_path,
    _validate_report,
    _validate_snapshot_list,
    _validate_string,
    build_snapshot_report,
    command_output,
    copy_if_exists,
    create_snapshot,
    list_snapshots,
    main,
    parse_args,
    print_report,
    print_snapshots,
    timestamp,
    write_json,
    write_log_reports,
    write_manifest,
    write_platform_reports,
    write_system_reports,
    write_text,
)
from betabox_robotics.version import __version__

MODULE = "betabox_robotics.services.snapshot"


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


def make_report(
    *,
    name: str = "snapshot-20260806-000000",
    path: str = "/tmp/snapshots/snapshot-20260806-000000",
    created_at: str = "2026-08-06 00:00:00",
    hostname: str = "Betabox-7eea",
    sdk_version: str = "1.0.0",
) -> SnapshotReport:
    return SnapshotReport(
        name=name,
        path=path,
        created_at=created_at,
        hostname=hostname,
        sdk_version=sdk_version,
    )


class ValidationTests(unittest.TestCase):
    def test_validate_config_accepts_config(self) -> None:
        self.assertIs(
            _validate_config(DEFAULT_PLATFORM_CONFIG),
            DEFAULT_PLATFORM_CONFIG,
        )

    def test_validate_config_rejects_invalid_value(self) -> None:
        for value in (
            None,
            object(),
            "config",
            1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "config must be a PlatformConfig",
                ),
            ):
                _validate_config(value)

    def test_validate_string_strips_value(self) -> None:
        self.assertEqual(
            _validate_string(
                " value ",
                name="field",
            ),
            "value",
        )

    def test_validate_string_rejects_invalid_type(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "field must be a string",
        ):
            _validate_string(
                1,
                name="field",
            )

    def test_validate_string_rejects_empty_value(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "field cannot be empty",
        ):
            _validate_string(
                " ",
                name="field",
            )

    def test_validate_path_accepts_path(self) -> None:
        path = Path("/tmp/snapshot")

        self.assertEqual(
            _validate_path(
                path,
                name="path",
            ),
            path,
        )

    def test_validate_path_strips_string(self) -> None:
        self.assertEqual(
            _validate_path(
                " /tmp/snapshot ",
                name="path",
            ),
            Path("/tmp/snapshot"),
        )

    def test_validate_path_expands_user(self) -> None:
        expanded = Path("/home/picar/snapshots")

        with patch.object(
            Path,
            "expanduser",
            return_value=expanded,
        ) as expanduser:
            result = _validate_path(
                "~/snapshots",
                name="path",
            )

        expanduser.assert_called_once_with()
        self.assertEqual(result, expanded)

    def test_validate_path_rejects_boolean(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "path must be a string or Path",
        ):
            _validate_path(
                True,
                name="path",
            )

    def test_validate_path_rejects_empty_string(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "path cannot be empty",
        ):
            _validate_path(
                " ",
                name="path",
            )

    def test_validate_command_normalizes_items(self) -> None:
        self.assertEqual(
            _validate_command(
                [
                    " hostname ",
                    " -I ",
                ]
            ),
            [
                "hostname",
                "-I",
            ],
        )

    def test_validate_command_rejects_non_list(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "command must be a list",
        ):
            _validate_command(
                ("hostname",)  # type: ignore[arg-type]
            )

    def test_validate_command_rejects_empty_list(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "command cannot be empty",
        ):
            _validate_command([])

    def test_validate_command_rejects_empty_item(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "command item cannot be empty",
        ):
            _validate_command(
                [
                    "hostname",
                    " ",
                ]
            )

    def test_validate_report_accepts_report(self) -> None:
        report = make_report()

        self.assertIs(
            _validate_report(report),
            report,
        )

    def test_validate_report_rejects_invalid_value(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "report must be a SnapshotReport",
        ):
            _validate_report(object())

    def test_validate_snapshot_list_accepts_tuple(self) -> None:
        snapshots = (
            Path("/tmp/one"),
            Path("/tmp/two"),
        )

        self.assertIs(
            _validate_snapshot_list(snapshots),
            snapshots,
        )

    def test_validate_snapshot_list_rejects_list(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "snapshots must be a tuple",
        ):
            _validate_snapshot_list(
                []  # type: ignore[arg-type]
            )

    def test_validate_snapshot_list_rejects_invalid_item(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "snapshots must contain only Path values",
        ):
            _validate_snapshot_list(
                ("snapshot",)  # type: ignore[arg-type]
            )


class SnapshotReportTests(unittest.TestCase):
    def test_accepts_valid_values(self) -> None:
        report = make_report()

        self.assertEqual(
            report.name,
            "snapshot-20260806-000000",
        )
        self.assertEqual(
            report.hostname,
            "Betabox-7eea",
        )

    def test_strips_string_fields(self) -> None:
        report = make_report(
            name=" snapshot-one ",
            path=" /tmp/snapshot-one ",
            created_at=" 2026-08-06 00:00:00 ",
            hostname=" Betabox-7eea ",
            sdk_version=" 1.0.0 ",
        )

        self.assertEqual(
            report.name,
            "snapshot-one",
        )
        self.assertEqual(
            report.path,
            "/tmp/snapshot-one",
        )
        self.assertEqual(
            report.created_at,
            "2026-08-06 00:00:00",
        )
        self.assertEqual(
            report.hostname,
            "Betabox-7eea",
        )
        self.assertEqual(
            report.sdk_version,
            "1.0.0",
        )

    def test_rejects_empty_name(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "name cannot be empty",
        ):
            make_report(name=" ")

    def test_rejects_invalid_path(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "path cannot be empty",
        ):
            make_report(path=" ")

    def test_is_frozen_and_slotted(self) -> None:
        report = make_report()

        self.assertFalse(
            hasattr(
                report,
                "__dict__",
            )
        )

        with self.assertRaises(FrozenInstanceError):
            report.name = "changed"  # type: ignore[misc]


class TimestampTests(unittest.TestCase):
    def test_returns_timestamp(self) -> None:
        with patch(
            f"{MODULE}.time.strftime",
            return_value="20260806-000000",
        ) as strftime:
            result = timestamp()

        strftime.assert_called_once_with("%Y%m%d-%H%M%S")
        self.assertEqual(
            result,
            "20260806-000000",
        )

    def test_rejects_empty_timestamp(self) -> None:
        with (
            patch(
                f"{MODULE}.time.strftime",
                return_value=" ",
            ),
            self.assertRaisesRegex(
                ValueError,
                "timestamp cannot be empty",
            ),
        ):
            timestamp()


class WriteTextTests(unittest.TestCase):
    def test_creates_parent_and_writes_text(self) -> None:
        path = Path("/tmp/snapshot/system/uname.txt")

        with (
            patch.object(
                Path,
                "mkdir",
            ) as mkdir,
            patch.object(
                Path,
                "write_text",
            ) as write,
        ):
            write_text(
                path,
                " Linux output ",
            )

        mkdir.assert_called_once_with(
            parents=True,
            exist_ok=True,
        )
        write.assert_called_once_with(
            "Linux output",
            encoding="utf-8",
        )

    def test_rejects_empty_content_before_filesystem(self) -> None:
        with (
            patch.object(
                Path,
                "mkdir",
            ) as mkdir,
            self.assertRaisesRegex(
                ValueError,
                "content cannot be empty",
            ),
        ):
            write_text(
                "/tmp/output.txt",
                " ",
            )

        mkdir.assert_not_called()

    def test_filesystem_error_propagates(self) -> None:
        error = OSError("permission denied")

        with (
            patch.object(
                Path,
                "mkdir",
                side_effect=error,
            ),
            self.assertRaises(OSError) as context,
        ):
            write_text(
                "/tmp/output.txt",
                "value",
            )

        self.assertIs(
            context.exception,
            error,
        )


class WriteJsonTests(unittest.TestCase):
    def test_creates_parent_and_writes_json(self) -> None:
        data = {
            "status": "ok",
        }

        with (
            patch.object(
                Path,
                "mkdir",
            ) as mkdir,
            patch.object(
                Path,
                "write_text",
            ) as write,
        ):
            write_json(
                "/tmp/status.json",
                data,
            )

        mkdir.assert_called_once_with(
            parents=True,
            exist_ok=True,
        )
        write.assert_called_once_with(
            json.dumps(
                data,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

    def test_uses_string_fallback_for_unknown_value(self) -> None:
        value = object()

        with (
            patch.object(
                Path,
                "mkdir",
            ),
            patch.object(
                Path,
                "write_text",
            ) as write,
        ):
            write_json(
                "/tmp/status.json",
                {
                    "value": value,
                },
            )

        content = write.call_args.args[0]

        self.assertIn(
            str(value),
            content,
        )

    def test_rejects_none_before_filesystem(self) -> None:
        with (
            patch.object(
                Path,
                "mkdir",
            ) as mkdir,
            self.assertRaisesRegex(
                ValueError,
                "data cannot be None",
            ),
        ):
            write_json(
                "/tmp/status.json",
                None,
            )

        mkdir.assert_not_called()


class CommandOutputTests(unittest.TestCase):
    def test_returns_stdout_for_success(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=" Linux output \n",
            ),
        ) as run:
            result = command_output(
                [
                    " uname ",
                    " -a ",
                ]
            )

        run.assert_called_once_with(
            [
                "uname",
                "-a",
            ]
        )
        self.assertEqual(
            result,
            "Linux output",
        )

    def test_returns_stderr_for_success_without_stdout(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stderr="warning",
            ),
        ):
            self.assertEqual(
                command_output(
                    [
                        "command",
                    ]
                ),
                "warning",
            )

    def test_returns_no_output_message(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(),
        ):
            self.assertEqual(
                command_output(
                    [
                        "command",
                    ]
                ),
                "(no output)",
            )

    def test_returns_failed_to_run_message(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=None,
        ):
            self.assertEqual(
                command_output(
                    [
                        "command",
                    ]
                ),
                "command failed to run",
            )

    def test_failed_command_prefers_stderr(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=2,
                stdout="stdout",
                stderr="stderr",
            ),
        ):
            self.assertEqual(
                command_output(
                    [
                        "command",
                    ]
                ),
                "stderr",
            )

    def test_failed_command_uses_status_without_output(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=2,
            ),
        ):
            self.assertEqual(
                command_output(
                    [
                        "command",
                    ]
                ),
                "command exited with status 2",
            )


class CopyIfExistsTests(unittest.TestCase):
    def test_missing_source_returns_false(self) -> None:
        with (
            patch.object(
                Path,
                "exists",
                return_value=False,
            ),
            patch(f"{MODULE}.shutil.copy2") as copy,
        ):
            result = copy_if_exists(
                "/tmp/source",
                "/tmp/destination",
            )

        self.assertFalse(result)
        copy.assert_not_called()

    def test_copies_file(self) -> None:
        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch.object(
                Path,
                "mkdir",
            ) as mkdir,
            patch.object(
                Path,
                "is_dir",
                return_value=False,
            ),
            patch(f"{MODULE}.shutil.copy2") as copy,
        ):
            result = copy_if_exists(
                "/tmp/source.log",
                "/tmp/snapshot/source.log",
            )

        self.assertTrue(result)
        mkdir.assert_called_once_with(
            parents=True,
            exist_ok=True,
        )
        copy.assert_called_once_with(
            Path("/tmp/source.log"),
            Path("/tmp/snapshot/source.log"),
        )

    def test_copies_directory(self) -> None:
        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch.object(
                Path,
                "mkdir",
            ),
            patch.object(
                Path,
                "is_dir",
                return_value=True,
            ),
            patch(f"{MODULE}.shutil.copytree") as copy,
        ):
            result = copy_if_exists(
                "/tmp/source",
                "/tmp/snapshot/source",
            )

        self.assertTrue(result)
        copy.assert_called_once_with(
            Path("/tmp/source"),
            Path("/tmp/snapshot/source"),
            dirs_exist_ok=True,
        )

    def test_os_error_returns_false(self) -> None:
        with patch.object(
            Path,
            "exists",
            side_effect=OSError("unavailable"),
        ):
            self.assertFalse(
                copy_if_exists(
                    "/tmp/source",
                    "/tmp/destination",
                )
            )


class BuildSnapshotReportTests(unittest.TestCase):
    def test_builds_generated_report(self) -> None:
        with (
            patch(
                f"{MODULE}.timestamp",
                return_value="20260806-000000",
            ) as timestamp_call,
            patch(
                f"{MODULE}.time.strftime",
                return_value="2026-08-06 00:00:00",
            ),
            patch(
                f"{MODULE}.socket.gethostname",
                return_value="Betabox-7eea",
            ),
        ):
            result = build_snapshot_report()

        timestamp_call.assert_called_once_with()
        self.assertEqual(
            result.name,
            "snapshot-20260806-000000",
        )
        self.assertEqual(
            result.path,
            str(
                DEFAULT_PLATFORM_CONFIG.paths.snapshot_root / "snapshot-20260806-000000"
            ),
        )
        self.assertEqual(
            result.created_at,
            "2026-08-06 00:00:00",
        )
        self.assertEqual(
            result.hostname,
            "Betabox-7eea",
        )
        self.assertEqual(
            result.sdk_version,
            __version__,
        )

    def test_uses_selected_name_without_timestamp(self) -> None:
        with (
            patch(f"{MODULE}.timestamp") as timestamp_call,
            patch(
                f"{MODULE}.time.strftime",
                return_value="2026-08-06 00:00:00",
            ),
            patch(
                f"{MODULE}.socket.gethostname",
                return_value="Betabox-7eea",
            ),
        ):
            result = build_snapshot_report(" classroom ")

        timestamp_call.assert_not_called()
        self.assertEqual(
            result.name,
            "classroom",
        )

    def test_rejects_invalid_config_before_collection(self) -> None:
        with (
            patch(f"{MODULE}.timestamp") as timestamp_call,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            build_snapshot_report(
                config=object(),  # type: ignore[arg-type]
            )

        timestamp_call.assert_not_called()

    def test_rejects_empty_hostname(self) -> None:
        with (
            patch(
                f"{MODULE}.timestamp",
                return_value="20260806-000000",
            ),
            patch(
                f"{MODULE}.time.strftime",
                return_value="2026-08-06 00:00:00",
            ),
            patch(
                f"{MODULE}.socket.gethostname",
                return_value=" ",
            ),
            self.assertRaisesRegex(
                ValueError,
                "hostname cannot be empty",
            ),
        ):
            build_snapshot_report()


class WriteManifestTests(unittest.TestCase):
    def test_writes_manifest(self) -> None:
        report = make_report()

        with patch(f"{MODULE}.write_json") as write:
            write_manifest(report)

        write.assert_called_once_with(
            Path(report.path) / "manifest.json",
            {
                "name": report.name,
                "path": report.path,
                "created_at": report.created_at,
                "hostname": report.hostname,
                "sdk_version": report.sdk_version,
            },
        )

    def test_rejects_invalid_report_before_write(self) -> None:
        with (
            patch(f"{MODULE}.write_json") as write,
            self.assertRaisesRegex(
                TypeError,
                "report must be a SnapshotReport",
            ),
        ):
            write_manifest(
                object()  # type: ignore[arg-type]
            )

        write.assert_not_called()


class WriteSystemReportsTests(unittest.TestCase):
    def test_writes_all_system_reports(self) -> None:
        snapshot_dir = Path("/tmp/snapshot")

        with (
            patch(
                f"{MODULE}.command_output",
                side_effect=lambda command: " ".join(command),
            ) as output,
            patch(f"{MODULE}.write_text") as write,
        ):
            write_system_reports(snapshot_dir)

        expected_commands = [list(command) for _, command in SYSTEM_COMMANDS]
        expected_commands.append(
            [
                "i2cdetect",
                "-y",
                str(DEFAULT_PLATFORM_CONFIG.verification.i2c_bus),
            ]
        )

        self.assertEqual(
            output.call_args_list,
            [call(command) for command in expected_commands],
        )

        expected_paths = [
            snapshot_dir / "system" / filename for filename, _ in SYSTEM_COMMANDS
        ]
        expected_paths.append(snapshot_dir / "system" / "i2cdetect.txt")

        self.assertEqual(
            [item.args[0] for item in write.call_args_list],
            expected_paths,
        )

    def test_rejects_invalid_config_before_commands(self) -> None:
        with (
            patch(f"{MODULE}.command_output") as output,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            write_system_reports(
                "/tmp/snapshot",
                config=object(),  # type: ignore[arg-type]
            )

        output.assert_not_called()


class WriteLogReportsTests(unittest.TestCase):
    def test_copies_logs_and_writes_journals(self) -> None:
        snapshot_dir = Path("/tmp/snapshot")
        config = DEFAULT_PLATFORM_CONFIG

        with (
            patch(f"{MODULE}.copy_if_exists") as copy,
            patch(
                f"{MODULE}.command_output",
                side_effect=(
                    "monitor journal",
                    "boot journal",
                ),
            ) as output,
            patch(f"{MODULE}.write_text") as write,
        ):
            write_log_reports(snapshot_dir)

        logs_dir = snapshot_dir / "logs"

        self.assertEqual(
            copy.call_args_list,
            [
                call(
                    config.paths.monitor_log,
                    logs_dir / "monitor.log",
                ),
                call(
                    config.paths.boot_announce_log,
                    logs_dir / "boot_announce.log",
                ),
            ],
        )
        self.assertEqual(
            output.call_args_list,
            [
                call(
                    [
                        "journalctl",
                        "-u",
                        config.services.monitor.unit,
                        "-n",
                        "100",
                        "--no-pager",
                    ]
                ),
                call(
                    [
                        "journalctl",
                        "-u",
                        config.services.boot_announce.unit,
                        "-n",
                        "100",
                        "--no-pager",
                    ]
                ),
            ],
        )
        self.assertEqual(
            write.call_args_list,
            [
                call(
                    logs_dir / "journal-betabox-monitor.txt",
                    "monitor journal",
                ),
                call(
                    logs_dir / "journal-boot-announce.txt",
                    "boot journal",
                ),
            ],
        )


class WritePlatformReportsTests(unittest.TestCase):
    def test_collects_and_writes_platform_reports(self) -> None:
        snapshot_dir = Path("/tmp/snapshot")
        status = SimpleNamespace(value="status")
        service = SimpleNamespace(value="service")
        check = SimpleNamespace(value="check")
        diagnosis = SimpleNamespace(value="diagnosis")

        with (
            patch(
                f"{MODULE}.collect_status",
                return_value=status,
            ) as collect_status,
            patch(
                f"{MODULE}.collect_services",
                return_value=(service,),
            ) as collect_services,
            patch(
                f"{MODULE}.collect_checks",
                return_value=(check,),
            ) as collect_checks,
            patch(
                f"{MODULE}.collect_diagnoses",
                return_value=(diagnosis,),
            ) as collect_diagnoses,
            patch(
                f"{MODULE}.asdict",
                side_effect=lambda value: {
                    "value": value.value,
                },
            ),
            patch(f"{MODULE}.write_json") as write,
        ):
            write_platform_reports(snapshot_dir)

        collect_status.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        collect_services.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        collect_checks.assert_called_once_with(config=DEFAULT_PLATFORM_CONFIG)
        collect_diagnoses.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        self.assertEqual(
            write.call_args_list,
            [
                call(
                    snapshot_dir / "status.json",
                    {
                        "value": "status",
                    },
                ),
                call(
                    snapshot_dir / "services.json",
                    [
                        {
                            "value": "service",
                        }
                    ],
                ),
                call(
                    snapshot_dir / "verify.json",
                    [
                        {
                            "value": "check",
                        }
                    ],
                ),
                call(
                    snapshot_dir / "doctor.json",
                    [
                        {
                            "value": "diagnosis",
                        }
                    ],
                ),
            ],
        )


class CreateSnapshotTests(unittest.TestCase):
    def test_creates_snapshot_in_order(self) -> None:
        report = make_report()

        with (
            patch(
                f"{MODULE}.build_snapshot_report",
                return_value=report,
            ) as build,
            patch.object(
                Path,
                "exists",
                return_value=False,
            ),
            patch(f"{MODULE}.write_manifest") as manifest,
            patch(f"{MODULE}.write_platform_reports") as platform,
            patch(f"{MODULE}.write_system_reports") as system,
            patch(f"{MODULE}.write_log_reports") as logs,
        ):
            result = create_snapshot(" classroom ")

        self.assertIs(
            result,
            report,
        )
        build.assert_called_once_with(
            " classroom ",
            config=DEFAULT_PLATFORM_CONFIG,
        )
        snapshot_dir = Path(report.path)
        manifest.assert_called_once_with(report)
        platform.assert_called_once_with(
            snapshot_dir,
            config=DEFAULT_PLATFORM_CONFIG,
        )
        system.assert_called_once_with(
            snapshot_dir,
            config=DEFAULT_PLATFORM_CONFIG,
        )
        logs.assert_called_once_with(
            snapshot_dir,
            config=DEFAULT_PLATFORM_CONFIG,
        )

    def test_existing_snapshot_raises_before_writes(self) -> None:
        report = make_report()

        with (
            patch(
                f"{MODULE}.build_snapshot_report",
                return_value=report,
            ),
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch(f"{MODULE}.write_manifest") as manifest,
            self.assertRaisesRegex(
                FileExistsError,
                report.path,
            ),
        ):
            create_snapshot(report.name)

        manifest.assert_not_called()

    def test_rejects_invalid_config_before_build(self) -> None:
        with (
            patch(f"{MODULE}.build_snapshot_report") as build,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            create_snapshot(
                config=object(),  # type: ignore[arg-type]
            )

        build.assert_not_called()


class ListSnapshotsTests(unittest.TestCase):
    def test_missing_root_returns_empty_tuple(self) -> None:
        with patch.object(
            Path,
            "exists",
            return_value=False,
        ):
            self.assertEqual(
                list_snapshots(),
                (),
            )

    def test_exists_error_returns_empty_tuple(self) -> None:
        with patch.object(
            Path,
            "exists",
            side_effect=OSError("permission denied"),
        ):
            self.assertEqual(
                list_snapshots(),
                (),
            )

    def test_returns_directories_in_reverse_order(self) -> None:
        paths = (
            Path("/snapshots/snapshot-1"),
            Path("/snapshots/file.txt"),
            Path("/snapshots/snapshot-3"),
            Path("/snapshots/snapshot-2"),
        )

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch.object(
                Path,
                "iterdir",
                return_value=iter(paths),
            ),
            patch.object(
                Path,
                "is_dir",
                side_effect=(
                    True,
                    False,
                    True,
                    True,
                ),
            ),
        ):
            result = list_snapshots()

        self.assertEqual(
            result,
            (
                Path("/snapshots/snapshot-3"),
                Path("/snapshots/snapshot-2"),
                Path("/snapshots/snapshot-1"),
            ),
        )


class PrintReportTests(unittest.TestCase):
    def test_prints_report(self) -> None:
        report = make_report()

        with patch("builtins.print") as print_message:
            print_report(report)

        self.assertIn(
            call(f"Name:    {report.name}"),
            print_message.call_args_list,
        )
        self.assertIn(
            call(f"Path:    {report.path}"),
            print_message.call_args_list,
        )
        self.assertIn(
            call(f"SDK:     {report.sdk_version}"),
            print_message.call_args_list,
        )

    def test_rejects_invalid_report_before_print(self) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                "report must be a SnapshotReport",
            ),
        ):
            print_report(
                object()  # type: ignore[arg-type]
            )

        print_message.assert_not_called()


class PrintSnapshotsTests(unittest.TestCase):
    def test_prints_no_snapshots(self) -> None:
        with patch("builtins.print") as print_message:
            print_snapshots(())

        self.assertIn(
            call("No snapshots found."),
            print_message.call_args_list,
        )

    def test_prints_snapshot_names(self) -> None:
        snapshots = (
            Path("/snapshots/snapshot-two"),
            Path("/snapshots/snapshot-one"),
        )

        with patch("builtins.print") as print_message:
            print_snapshots(snapshots)

        self.assertIn(
            call("snapshot-two"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("snapshot-one"),
            print_message.call_args_list,
        )

    def test_rejects_invalid_collection_before_print(self) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                "snapshots must be a tuple",
            ),
        ):
            print_snapshots(
                []  # type: ignore[arg-type]
            )

        print_message.assert_not_called()


class ParserTests(unittest.TestCase):
    def test_build_parser(self) -> None:
        parser = _build_parser()

        self.assertIsInstance(
            parser,
            argparse.ArgumentParser,
        )
        self.assertEqual(
            parser.prog,
            "betabox snapshot",
        )

    def test_defaults(self) -> None:
        args = parse_args([])

        self.assertFalse(args.list)
        self.assertIsNone(args.name)

    def test_parses_list(self) -> None:
        args = parse_args(
            [
                "--list",
            ]
        )

        self.assertTrue(args.list)

    def test_parses_name(self) -> None:
        args = parse_args(
            [
                "--name",
                "classroom",
            ]
        )

        self.assertEqual(
            args.name,
            "classroom",
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


class MainTests(unittest.TestCase):
    def test_lists_snapshots(self) -> None:
        snapshots = (Path("/snapshots/one"),)

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(
                    list=True,
                    name=None,
                ),
            ) as parse,
            patch(
                f"{MODULE}.list_snapshots",
                return_value=snapshots,
            ) as list_call,
            patch(f"{MODULE}.print_snapshots") as print_call,
            patch(f"{MODULE}.create_snapshot") as create,
        ):
            result = main(
                [
                    "--list",
                ]
            )

        self.assertEqual(result, 0)
        parse.assert_called_once_with(
            [
                "--list",
            ]
        )
        list_call.assert_called_once_with()
        print_call.assert_called_once_with(snapshots)
        create.assert_not_called()

    def test_creates_named_snapshot(self) -> None:
        report = make_report(name="classroom")

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(
                    list=False,
                    name="classroom",
                ),
            ),
            patch(
                f"{MODULE}.create_snapshot",
                return_value=report,
            ) as create,
            patch(f"{MODULE}.print_report") as print_call,
        ):
            result = main(
                [
                    "--name",
                    "classroom",
                ]
            )

        self.assertEqual(result, 0)
        create.assert_called_once_with("classroom")
        print_call.assert_called_once_with(report)

    def test_existing_snapshot_returns_error(self) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(
                    list=False,
                    name="classroom",
                ),
            ),
            patch(
                f"{MODULE}.create_snapshot",
                side_effect=FileExistsError("exists"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(result, 1)
        print_message.assert_called_once_with("Snapshot already exists: classroom")


if __name__ == "__main__":
    unittest.main()
