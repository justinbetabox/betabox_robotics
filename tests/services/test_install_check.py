from __future__ import annotations

import argparse
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.accounts import (
    BETABOX_ACCOUNTS,
)
from betabox_robotics.services.install_check import (
    collect_checks,
    main,
    parse_args,
    print_results,
    resolve_service_user,
)
from betabox_robotics.services.install_checks import (
    CheckResult,
)

MODULE = "betabox_robotics.services.install_check"


def make_check(
    name: str,
    *,
    ok: bool = True,
    message: str = "",
) -> CheckResult:
    return CheckResult(
        name=name,
        ok=ok,
        message=message,
    )


class ResolveServiceUserTests(unittest.TestCase):
    def test_uses_requested_user(self) -> None:
        with (
            patch.dict(
                f"{MODULE}.os.environ",
                {
                    "SUDO_USER": "sudo-user",
                },
            ),
            patch(f"{MODULE}.os.getuid") as getuid,
            patch(f"{MODULE}.pwd.getpwuid") as getpwuid,
        ):
            result = resolve_service_user(" picar ")

        self.assertEqual(
            result,
            "picar",
        )
        getuid.assert_not_called()
        getpwuid.assert_not_called()

    def test_requested_user_precedes_sudo_user(
        self,
    ) -> None:
        with patch.dict(
            f"{MODULE}.os.environ",
            {
                "SUDO_USER": "sudo-user",
            },
        ):
            result = resolve_service_user("requested-user")

        self.assertEqual(
            result,
            "requested-user",
        )

    def test_uses_sudo_user(self) -> None:
        with (
            patch.dict(
                f"{MODULE}.os.environ",
                {
                    "SUDO_USER": " picar ",
                },
            ),
            patch(f"{MODULE}.os.getuid") as getuid,
            patch(f"{MODULE}.pwd.getpwuid") as getpwuid,
        ):
            result = resolve_service_user()

        self.assertEqual(
            result,
            "picar",
        )
        getuid.assert_not_called()
        getpwuid.assert_not_called()

    def test_empty_sudo_user_falls_back_to_uid(
        self,
    ) -> None:
        user = SimpleNamespace(pw_name="picar")

        with (
            patch.dict(
                f"{MODULE}.os.environ",
                {
                    "SUDO_USER": "   ",
                },
            ),
            patch(
                f"{MODULE}.os.getuid",
                return_value=1000,
            ) as getuid,
            patch(
                f"{MODULE}.pwd.getpwuid",
                return_value=user,
            ) as getpwuid,
        ):
            result = resolve_service_user()

        self.assertEqual(
            result,
            "picar",
        )
        getuid.assert_called_once_with()
        getpwuid.assert_called_once_with(1000)

    def test_missing_sudo_user_falls_back_to_uid(
        self,
    ) -> None:
        user = SimpleNamespace(pw_name="picar")

        with (
            patch.dict(
                f"{MODULE}.os.environ",
                {},
                clear=True,
            ),
            patch(
                f"{MODULE}.os.getuid",
                return_value=1000,
            ) as getuid,
            patch(
                f"{MODULE}.pwd.getpwuid",
                return_value=user,
            ) as getpwuid,
        ):
            result = resolve_service_user()

        self.assertEqual(
            result,
            "picar",
        )
        getuid.assert_called_once_with()
        getpwuid.assert_called_once_with(1000)

    def test_strips_uid_account_name(self) -> None:
        with (
            patch.dict(
                f"{MODULE}.os.environ",
                {},
                clear=True,
            ),
            patch(
                f"{MODULE}.os.getuid",
                return_value=1000,
            ),
            patch(
                f"{MODULE}.pwd.getpwuid",
                return_value=SimpleNamespace(pw_name=" picar "),
            ),
        ):
            result = resolve_service_user()

        self.assertEqual(
            result,
            "picar",
        )

    def test_rejects_invalid_requested_user_before_environment(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.os.environ.get") as get_environment,
            patch(f"{MODULE}.os.getuid") as getuid,
            self.assertRaisesRegex(
                TypeError,
                ("requested_user must be a string"),
            ),
        ):
            resolve_service_user(
                123  # type: ignore[arg-type]
            )

        get_environment.assert_not_called()
        getuid.assert_not_called()

    def test_rejects_empty_requested_user(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.os.environ.get") as get_environment,
            self.assertRaisesRegex(
                ValueError,
                ("requested_user cannot be empty"),
            ),
        ):
            resolve_service_user(" ")

        get_environment.assert_not_called()

    def test_rejects_empty_uid_account_name(
        self,
    ) -> None:
        with (
            patch.dict(
                f"{MODULE}.os.environ",
                {},
                clear=True,
            ),
            patch(
                f"{MODULE}.os.getuid",
                return_value=1000,
            ),
            patch(
                f"{MODULE}.pwd.getpwuid",
                return_value=SimpleNamespace(pw_name=" "),
            ),
            self.assertRaisesRegex(
                ValueError,
                ("service user cannot be empty"),
            ),
        ):
            resolve_service_user()

    def test_uid_lookup_error_propagates(self) -> None:
        error = KeyError("UID not found")

        with (
            patch.dict(
                f"{MODULE}.os.environ",
                {},
                clear=True,
            ),
            patch(
                f"{MODULE}.os.getuid",
                return_value=1000,
            ),
            patch(
                f"{MODULE}.pwd.getpwuid",
                side_effect=error,
            ),
            self.assertRaises(KeyError) as context,
        ):
            resolve_service_user()

        self.assertIs(
            context.exception,
            error,
        )


class CollectChecksTests(unittest.TestCase):
    def test_collects_all_checks_in_order(self) -> None:
        verification = DEFAULT_PLATFORM_CONFIG.verification
        units = DEFAULT_PLATFORM_CONFIG.services.all_units
        betabox_command = str(Path("/opt/betabox/venv/bin/python").parent / "betabox")

        import_results = tuple(
            make_check(f"import:{module}")
            for module in (verification.required_python_modules)
        )
        cli_result = make_check("cli:betabox")
        launchpad_result = make_check("cli:betabox-launchpad")
        config_results = tuple(
            make_check(f"config:{line}")
            for line in (verification.required_boot_config_lines)
        )
        workspace_results = tuple(
            make_check(f"workspace:{account.username}") for account in BETABOX_ACCOUNTS
        )
        runtime_result = make_check("runtime-media:picar")
        executable_results = tuple(
            make_check(f"command:{executable}")
            for executable in (verification.required_executables)
        )
        installed_results = tuple(
            make_check(f"service-installed:{unit}") for unit in units
        )
        enabled_results = tuple(make_check(f"service-enabled:{unit}") for unit in units)
        avahi_result = make_check("systemd-override:avahi-daemon")

        with (
            patch(
                f"{MODULE}.sys.executable",
                ("/opt/betabox/venv/bin/python"),
            ),
            patch(
                f"{MODULE}.check_import",
                side_effect=import_results,
            ) as check_import,
            patch(
                f"{MODULE}.check_command",
                side_effect=[
                    cli_result,
                    launchpad_result,
                ],
            ) as check_command,
            patch(
                f"{MODULE}.check_config_line",
                side_effect=config_results,
            ) as check_config_line,
            patch(
                f"{MODULE}.check_account_workspace",
                side_effect=workspace_results,
            ) as check_workspace,
            patch(
                f"{MODULE}.check_runtime_media",
                return_value=runtime_result,
            ) as check_runtime,
            patch(
                f"{MODULE}.check_executable",
                side_effect=executable_results,
            ) as check_executable,
            patch(
                f"{MODULE}.check_service_installed",
                side_effect=installed_results,
            ) as check_installed,
            patch(
                f"{MODULE}.check_service_enabled",
                side_effect=enabled_results,
            ) as check_enabled,
            patch(
                f"{MODULE}.check_avahi_override",
                return_value=avahi_result,
            ) as check_avahi,
        ):
            result = collect_checks(
                DEFAULT_PLATFORM_CONFIG,
                service_user="picar",
            )

        expected: list[CheckResult] = [
            *import_results,
            cli_result,
            launchpad_result,
            *config_results,
            *workspace_results,
            runtime_result,
            *executable_results,
        ]

        for installed, enabled in zip(
            installed_results,
            enabled_results,
            strict=True,
        ):
            expected.extend(
                (
                    installed,
                    enabled,
                )
            )

        expected.append(avahi_result)

        self.assertEqual(
            result,
            tuple(expected),
        )
        self.assertIsInstance(
            result,
            tuple,
        )

        self.assertEqual(
            check_import.call_args_list,
            [call(module) for module in (verification.required_python_modules)],
        )
        self.assertEqual(
            check_command.call_args_list,
            [
                call(
                    [
                        betabox_command,
                        "--help",
                    ],
                    "cli:betabox",
                    timeout=(verification.command_timeout_seconds),
                ),
                call(
                    [
                        betabox_command,
                        "launchpad",
                        "--help",
                    ],
                    "cli:betabox-launchpad",
                    timeout=(verification.command_timeout_seconds),
                ),
            ],
        )
        self.assertEqual(
            check_config_line.call_args_list,
            [
                call(
                    line,
                    DEFAULT_PLATFORM_CONFIG,
                )
                for line in (verification.required_boot_config_lines)
            ],
        )
        self.assertEqual(
            check_workspace.call_args_list,
            [
                call(
                    account.username,
                    account.home,
                )
                for account in BETABOX_ACCOUNTS
            ],
        )
        check_runtime.assert_called_once_with("picar")
        self.assertEqual(
            check_executable.call_args_list,
            [call(executable) for executable in (verification.required_executables)],
        )
        self.assertEqual(
            check_installed.call_args_list,
            [call(unit) for unit in units],
        )
        self.assertEqual(
            check_enabled.call_args_list,
            [
                call(
                    unit,
                    timeout=(verification.command_timeout_seconds),
                )
                for unit in units
            ],
        )
        check_avahi.assert_called_once_with()

    def test_strips_service_user(self) -> None:
        with (
            patch(
                f"{MODULE}.check_import",
                return_value=make_check("import:test"),
            ),
            patch(
                f"{MODULE}.check_command",
                return_value=make_check("cli:test"),
            ),
            patch(
                f"{MODULE}.check_config_line",
                return_value=make_check("config:test"),
            ),
            patch(
                f"{MODULE}.check_account_workspace",
                return_value=make_check("workspace:test"),
            ),
            patch(
                f"{MODULE}.check_runtime_media",
                return_value=make_check("runtime-media:picar"),
            ) as check_runtime,
            patch(
                f"{MODULE}.check_executable",
                return_value=make_check("command:test"),
            ),
            patch(
                f"{MODULE}.check_service_installed",
                return_value=make_check("service-installed:test"),
            ),
            patch(
                f"{MODULE}.check_service_enabled",
                return_value=make_check("service-enabled:test"),
            ),
            patch(
                f"{MODULE}.check_avahi_override",
                return_value=make_check("systemd-override:test"),
            ),
        ):
            collect_checks(service_user=" picar ")

        check_runtime.assert_called_once_with("picar")

    def test_rejects_invalid_config_before_checks(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.check_import") as check_import,
            patch(f"{MODULE}.check_command") as check_command,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            collect_checks(
                object(),  # type: ignore[arg-type]
                service_user="picar",
            )

        check_import.assert_not_called()
        check_command.assert_not_called()

    def test_rejects_invalid_service_user_before_checks(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.check_import") as check_import,
            self.assertRaisesRegex(
                TypeError,
                ("service_user must be a string"),
            ),
        ):
            collect_checks(
                service_user=123,  # type: ignore[arg-type]
            )

        check_import.assert_not_called()

    def test_rejects_empty_service_user_before_checks(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.check_import") as check_import,
            self.assertRaisesRegex(
                ValueError,
                ("service_user cannot be empty"),
            ),
        ):
            collect_checks(service_user=" ")

        check_import.assert_not_called()

    def test_dependency_error_propagates(self) -> None:
        error = RuntimeError("check failed unexpectedly")

        with (
            patch(
                f"{MODULE}.check_import",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_checks(service_user="picar")

        self.assertIs(
            context.exception,
            error,
        )


class PrintResultsTests(unittest.TestCase):
    def test_prints_all_passing_results(self) -> None:
        checks = (
            make_check(
                "import:aiohttp",
                message="3.12.0",
            ),
            make_check(
                "command:ffmpeg",
                message="/usr/bin/ffmpeg",
            ),
        )

        with patch("builtins.print") as print_message:
            result = print_results(checks)

        self.assertTrue(result)
        self.assertEqual(
            print_message.call_args_list,
            [
                call(),
                call("Betabox Install Check"),
                call("====================="),
                call(),
                call("[OK] import:aiohttp"),
                call("     3.12.0"),
                call("[OK] command:ffmpeg"),
                call("     /usr/bin/ffmpeg"),
                call(),
                call("Betabox installation check passed."),
                call(),
                call("A reboot is required before hardware verification."),
                call(),
                call("After reboot:"),
                call("  source /opt/betabox/venv/bin/activate"),
                call("  betabox verify"),
                call("  betabox doctor"),
            ],
        )

    def test_prints_failed_results(self) -> None:
        checks = (
            make_check(
                "import:aiohttp",
                message="import ok",
            ),
            make_check(
                "command:missing",
                ok=False,
                message="not found",
            ),
        )

        with patch("builtins.print") as print_message:
            result = print_results(checks)

        self.assertFalse(result)
        self.assertEqual(
            print_message.call_args_list,
            [
                call(),
                call("Betabox Install Check"),
                call("====================="),
                call(),
                call("[OK] import:aiohttp"),
                call("     import ok"),
                call("[FAIL] command:missing"),
                call("     not found"),
                call(),
                call("Betabox installation check failed."),
            ],
        )

    def test_empty_checks_passes(self) -> None:
        with patch("builtins.print"):
            result = print_results(())

        self.assertTrue(result)

    def test_does_not_print_empty_message(self) -> None:
        checks = (make_check("check:test"),)

        with patch("builtins.print") as print_message:
            print_results(checks)

        self.assertNotIn(
            call("     "),
            print_message.call_args_list,
        )

    def test_reports_each_failed_check(self) -> None:
        checks = (
            make_check(
                "check:one",
                ok=False,
            ),
            make_check(
                "check:two",
                ok=False,
            ),
        )

        with patch("builtins.print") as print_message:
            result = print_results(checks)

        self.assertFalse(result)
        self.assertIn(
            call("[FAIL] check:one"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("[FAIL] check:two"),
            print_message.call_args_list,
        )

    def test_rejects_non_tuple_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                "checks must be a tuple",
            ),
        ):
            print_results(
                []  # type: ignore[arg-type]
            )

        print_message.assert_not_called()

    def test_rejects_invalid_check_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                ("checks must contain only CheckResult values"),
            ),
        ):
            print_results(
                (
                    object(),  # type: ignore[arg-type]
                )
            )

        print_message.assert_not_called()


class ParseArgsTests(unittest.TestCase):
    def test_defaults_service_user_to_none(
        self,
    ) -> None:
        args = parse_args([])

        self.assertIsInstance(
            args,
            argparse.Namespace,
        )
        self.assertIsNone(args.service_user)

    def test_parses_service_user(self) -> None:
        args = parse_args(
            [
                "--service-user",
                "picar",
            ]
        )

        self.assertEqual(
            args.service_user,
            "picar",
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

    def test_rejects_missing_service_user_value(
        self,
    ) -> None:
        with (
            patch("sys.stderr"),
            self.assertRaises(SystemExit),
        ):
            parse_args(
                [
                    "--service-user",
                ]
            )


class MainTests(unittest.TestCase):
    def test_returns_zero_when_checks_pass(
        self,
    ) -> None:
        args = argparse.Namespace(service_user="picar")
        checks = (make_check("check:test"),)

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=args,
            ) as parse_args_call,
            patch(
                f"{MODULE}.resolve_service_user",
                return_value="picar",
            ) as resolve_user,
            patch(
                f"{MODULE}.collect_checks",
                return_value=checks,
            ) as collect,
            patch(
                f"{MODULE}.print_results",
                return_value=True,
            ) as print_results_call,
        ):
            result = main(
                [
                    "--service-user",
                    "picar",
                ]
            )

        self.assertEqual(
            result,
            0,
        )
        parse_args_call.assert_called_once_with(
            [
                "--service-user",
                "picar",
            ]
        )
        resolve_user.assert_called_once_with("picar")
        collect.assert_called_once_with(
            DEFAULT_PLATFORM_CONFIG,
            service_user="picar",
        )
        print_results_call.assert_called_once_with(checks)

    def test_returns_one_when_checks_fail(
        self,
    ) -> None:
        checks = (
            make_check(
                "check:test",
                ok=False,
            ),
        )

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(service_user=None),
            ),
            patch(
                f"{MODULE}.resolve_service_user",
                return_value="picar",
            ),
            patch(
                f"{MODULE}.collect_checks",
                return_value=checks,
            ),
            patch(
                f"{MODULE}.print_results",
                return_value=False,
            ),
        ):
            result = main([])

        self.assertEqual(
            result,
            1,
        )

    def test_returns_one_for_resolution_type_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(service_user=None),
            ),
            patch(
                f"{MODULE}.resolve_service_user",
                side_effect=TypeError("invalid user"),
            ),
            patch(f"{MODULE}.collect_checks") as collect,
            patch(f"{MODULE}.print_results") as print_results_call,
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once_with("invalid user")
        collect.assert_not_called()
        print_results_call.assert_not_called()

    def test_returns_one_for_collection_value_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(service_user="picar"),
            ),
            patch(
                f"{MODULE}.resolve_service_user",
                return_value="picar",
            ),
            patch(
                f"{MODULE}.collect_checks",
                side_effect=ValueError("invalid configuration"),
            ),
            patch(f"{MODULE}.print_results") as print_results_call,
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once_with("invalid configuration")
        print_results_call.assert_not_called()

    def test_returns_one_for_uid_lookup_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(service_user=None),
            ),
            patch(
                f"{MODULE}.resolve_service_user",
                side_effect=KeyError("UID not found"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once()

    def test_returns_one_for_environment_os_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(service_user=None),
            ),
            patch(
                f"{MODULE}.resolve_service_user",
                side_effect=OSError("account database failed"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once_with("account database failed")

    def test_unexpected_resolution_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(service_user=None),
            ),
            patch(
                f"{MODULE}.resolve_service_user",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            main([])

        self.assertIs(
            context.exception,
            error,
        )

    def test_unexpected_collection_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(service_user="picar"),
            ),
            patch(
                f"{MODULE}.resolve_service_user",
                return_value="picar",
            ),
            patch(
                f"{MODULE}.collect_checks",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            main([])

        self.assertIs(
            context.exception,
            error,
        )

    def test_print_results_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("printing failed")
        checks = (make_check("check:test"),)

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(service_user="picar"),
            ),
            patch(
                f"{MODULE}.resolve_service_user",
                return_value="picar",
            ),
            patch(
                f"{MODULE}.collect_checks",
                return_value=checks,
            ),
            patch(
                f"{MODULE}.print_results",
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
