from __future__ import annotations

import argparse
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, patch

from betabox_robotics.services.guest import (
    DEFAULT_REPOSITORY_ROOT,
    GuestWorkspaceStatus,
    _build_parser,
    _validate_path,
    guest_account,
    guest_status,
    main,
    parse_args,
    print_status,
    provision_guest,
    require_root,
    reset_guest,
)

MODULE = "betabox_robotics.services.guest"


def make_account(
    *,
    username: str = "guest",
    home: Path = Path("/home/guest"),
    persistent: bool = False,
    install_media: bool = True,
):
    return SimpleNamespace(
        username=username,
        home=home,
        persistent=persistent,
        install_media=install_media,
    )


def make_status(
    *,
    account_exists: bool = True,
    home_exists: bool = True,
    curriculum_exists: bool = True,
    media_exists: bool = True,
    preferences_exist: bool = True,
) -> GuestWorkspaceStatus:
    return GuestWorkspaceStatus(
        account_exists=account_exists,
        home_exists=home_exists,
        curriculum_exists=curriculum_exists,
        media_exists=media_exists,
        preferences_exist=preferences_exist,
    )


class ValidatePathTests(unittest.TestCase):
    def test_accepts_path(self) -> None:
        path = Path("/opt/libs/betabox_robotics")

        result = _validate_path(
            path,
            name="repository_root",
        )

        self.assertEqual(result, path)

    def test_accepts_string(self) -> None:
        result = _validate_path(
            "/opt/libs/betabox_robotics",
            name="repository_root",
        )

        self.assertEqual(
            result,
            Path("/opt/libs/betabox_robotics"),
        )

    def test_strips_string(self) -> None:
        result = _validate_path(
            " /opt/libs/betabox_robotics ",
            name="repository_root",
        )

        self.assertEqual(
            result,
            Path("/opt/libs/betabox_robotics"),
        )

    def test_expands_user(self) -> None:
        expanded = Path("/home/picar/betabox_robotics")

        with patch.object(
            Path,
            "expanduser",
            return_value=expanded,
        ) as expanduser:
            result = _validate_path(
                "~/betabox_robotics",
                name="repository_root",
            )

        expanduser.assert_called_once_with()
        self.assertEqual(result, expanded)

    def test_rejects_boolean(self) -> None:
        for value in (True, False):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("repository_root must be a string or Path"),
                ),
            ):
                _validate_path(
                    value,
                    name="repository_root",
                )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            None,
            123,
            1.5,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("repository_root must be a string or Path"),
                ),
            ):
                _validate_path(
                    value,
                    name="repository_root",
                )

    def test_rejects_empty_string(self) -> None:
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
                    ("repository_root cannot be empty"),
                ),
            ):
                _validate_path(
                    value,
                    name="repository_root",
                )


class GuestWorkspaceStatusTests(unittest.TestCase):
    def test_accepts_valid_values(self) -> None:
        status = make_status()

        self.assertTrue(status.account_exists)
        self.assertTrue(status.home_exists)
        self.assertTrue(status.curriculum_exists)
        self.assertTrue(status.media_exists)
        self.assertTrue(status.preferences_exist)

    def test_ok_when_every_value_is_true(
        self,
    ) -> None:
        self.assertTrue(make_status().ok)

    def test_not_ok_when_any_value_is_false(
        self,
    ) -> None:
        fields = (
            "account_exists",
            "home_exists",
            "curriculum_exists",
            "media_exists",
            "preferences_exist",
        )

        for field in fields:
            with self.subTest(field=field):
                values = {name: True for name in fields}
                values[field] = False

                status = GuestWorkspaceStatus(**values)

                self.assertFalse(status.ok)

    def test_rejects_non_boolean_values(
        self,
    ) -> None:
        fields = (
            "account_exists",
            "home_exists",
            "curriculum_exists",
            "media_exists",
            "preferences_exist",
        )

        for field in fields:
            with self.subTest(field=field):
                values: dict[str, object] = {name: True for name in fields}
                values[field] = 1

                with self.assertRaisesRegex(
                    TypeError,
                    f"{field} must be a boolean",
                ):
                    GuestWorkspaceStatus(
                        **values  # type: ignore[arg-type]
                    )

    def test_is_frozen(self) -> None:
        status = make_status()

        with self.assertRaises(FrozenInstanceError):
            status.home_exists = False  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        status = make_status()

        self.assertFalse(
            hasattr(
                status,
                "__dict__",
            )
        )


class GuestAccountTests(unittest.TestCase):
    def test_returns_guest_account(self) -> None:
        account = make_account()

        with patch(
            f"{MODULE}.account_by_username",
            return_value=account,
        ) as account_lookup:
            result = guest_account()

        account_lookup.assert_called_once_with("guest")
        self.assertIs(result, account)

    def test_lookup_error_propagates(self) -> None:
        error = LookupError("guest account missing")

        with (
            patch(
                f"{MODULE}.account_by_username",
                side_effect=error,
            ),
            self.assertRaises(LookupError) as context,
        ):
            guest_account()

        self.assertIs(
            context.exception,
            error,
        )


class RequireRootTests(unittest.TestCase):
    def test_accepts_root(self) -> None:
        with patch(
            f"{MODULE}.os.geteuid",
            return_value=0,
        ):
            result = require_root()

        self.assertIsNone(result)

    def test_rejects_non_root(self) -> None:
        with (
            patch(
                f"{MODULE}.os.geteuid",
                return_value=1000,
            ),
            self.assertRaisesRegex(
                PermissionError,
                ("Guest workspace management requires root"),
            ),
        ):
            require_root()

    def test_unexpected_uid_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("uid lookup failed")

        with (
            patch(
                f"{MODULE}.os.geteuid",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            require_root()

        self.assertIs(
            context.exception,
            error,
        )


class ProvisionGuestTests(unittest.TestCase):
    def test_creates_workspace_and_populates_media(
        self,
    ) -> None:
        account = make_account()
        repository_root = Path("/opt/libs/betabox_robotics")

        with (
            patch(f"{MODULE}.require_root") as require_root_call,
            patch(
                f"{MODULE}.guest_account",
                return_value=account,
            ) as get_account,
            patch(f"{MODULE}.create_workspace") as create_workspace,
            patch(f"{MODULE}.populate_media") as populate_media,
        ):
            result = provision_guest(
                repository_root=repository_root,
            )

        self.assertIsNone(result)
        require_root_call.assert_called_once_with()
        get_account.assert_called_once_with()
        create_workspace.assert_called_once_with(account)
        populate_media.assert_called_once_with(
            repository_root,
            accounts=(account,),
        )

    def test_skips_media_when_disabled(
        self,
    ) -> None:
        account = make_account(install_media=False)

        with (
            patch(f"{MODULE}.require_root"),
            patch(
                f"{MODULE}.guest_account",
                return_value=account,
            ),
            patch(f"{MODULE}.create_workspace") as create_workspace,
            patch(f"{MODULE}.populate_media") as populate_media,
        ):
            provision_guest()

        create_workspace.assert_called_once_with(account)
        populate_media.assert_not_called()

    def test_uses_default_repository_root(
        self,
    ) -> None:
        account = make_account()

        with (
            patch(f"{MODULE}.require_root"),
            patch(
                f"{MODULE}.guest_account",
                return_value=account,
            ),
            patch(f"{MODULE}.create_workspace"),
            patch(f"{MODULE}.populate_media") as populate_media,
        ):
            provision_guest()

        populate_media.assert_called_once_with(
            DEFAULT_REPOSITORY_ROOT,
            accounts=(account,),
        )

    def test_rejects_invalid_path_before_root_check(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.require_root") as require_root_call,
            self.assertRaisesRegex(
                TypeError,
                ("repository_root must be a string or Path"),
            ),
        ):
            provision_guest(
                repository_root=True,  # type: ignore[arg-type]
            )

        require_root_call.assert_not_called()

    def test_root_error_stops_provisioning(
        self,
    ) -> None:
        error = PermissionError("root required")

        with (
            patch(
                f"{MODULE}.require_root",
                side_effect=error,
            ),
            patch(f"{MODULE}.guest_account") as get_account,
            self.assertRaises(PermissionError) as context,
        ):
            provision_guest()

        self.assertIs(
            context.exception,
            error,
        )
        get_account.assert_not_called()

    def test_workspace_error_propagates(
        self,
    ) -> None:
        account = make_account()
        error = OSError("workspace failed")

        with (
            patch(f"{MODULE}.require_root"),
            patch(
                f"{MODULE}.guest_account",
                return_value=account,
            ),
            patch(
                f"{MODULE}.create_workspace",
                side_effect=error,
            ),
            patch(f"{MODULE}.populate_media") as populate_media,
            self.assertRaises(OSError) as context,
        ):
            provision_guest()

        self.assertIs(
            context.exception,
            error,
        )
        populate_media.assert_not_called()


class ResetGuestTests(unittest.TestCase):
    def test_removes_children_and_reprovisions(
        self,
    ) -> None:
        home = Path("/home/guest")
        account = make_account(home=home)
        directory = home / "curriculum"
        file_path = home / "notes.txt"
        symlink = home / "media-link"

        with (
            patch(f"{MODULE}.require_root") as require_root_call,
            patch(
                f"{MODULE}.guest_account",
                return_value=account,
            ),
            patch.object(
                Path,
                "is_dir",
                side_effect=(
                    True,  # account.home
                    True,  # directory
                    False,  # file_path
                    True,  # symlink target appears directory-like
                ),
            ),
            patch.object(
                Path,
                "is_symlink",
                side_effect=(
                    False,  # account.home
                    False,  # directory
                    True,  # symlink
                ),
            ),
            patch.object(
                Path,
                "iterdir",
                return_value=iter(
                    (
                        directory,
                        file_path,
                        symlink,
                    )
                ),
            ),
            patch(f"{MODULE}.shutil.rmtree") as rmtree,
            patch.object(Path, "unlink") as unlink,
            patch(f"{MODULE}.provision_guest") as provision,
        ):
            reset_guest(repository_root=("/opt/libs/betabox_robotics"))

        require_root_call.assert_called_once_with()
        rmtree.assert_called_once_with(directory)
        self.assertEqual(
            unlink.call_count,
            2,
        )
        provision.assert_called_once_with(
            repository_root=Path("/opt/libs/betabox_robotics"),
        )

    def test_rejects_persistent_account(
        self,
    ) -> None:
        account = make_account(persistent=True)

        with (
            patch(f"{MODULE}.require_root"),
            patch(
                f"{MODULE}.guest_account",
                return_value=account,
            ),
            patch.object(Path, "iterdir") as iterdir,
            self.assertRaisesRegex(
                RuntimeError,
                ("Refusing to reset a persistent account"),
            ),
        ):
            reset_guest()

        iterdir.assert_not_called()

    def test_rejects_unexpected_home_path(
        self,
    ) -> None:
        account = make_account(home=Path("/tmp/guest"))

        with (
            patch(f"{MODULE}.require_root"),
            patch(
                f"{MODULE}.guest_account",
                return_value=account,
            ),
            self.assertRaisesRegex(
                RuntimeError,
                ("Refusing to reset unexpected path"),
            ),
        ):
            reset_guest()

    def test_rejects_missing_home_directory(
        self,
    ) -> None:
        account = make_account()

        with (
            patch(f"{MODULE}.require_root"),
            patch(
                f"{MODULE}.guest_account",
                return_value=account,
            ),
            patch.object(
                Path,
                "is_dir",
                return_value=False,
            ),
            self.assertRaisesRegex(
                RuntimeError,
                ("Guest home directory does not exist"),
            ),
        ):
            reset_guest()

    def test_rejects_symlinked_home(
        self,
    ) -> None:
        account = make_account()

        with (
            patch(f"{MODULE}.require_root"),
            patch(
                f"{MODULE}.guest_account",
                return_value=account,
            ),
            patch.object(
                Path,
                "is_dir",
                return_value=True,
            ),
            patch.object(
                Path,
                "is_symlink",
                return_value=True,
            ),
            patch.object(Path, "iterdir") as iterdir,
            self.assertRaisesRegex(
                RuntimeError,
                ("Refusing to reset a symlinked Guest home"),
            ),
        ):
            reset_guest()

        iterdir.assert_not_called()

    def test_directory_symlink_is_unlinked(
        self,
    ) -> None:
        account = make_account()
        child = account.home / "linked-directory"

        with (
            patch(f"{MODULE}.require_root"),
            patch(
                f"{MODULE}.guest_account",
                return_value=account,
            ),
            patch.object(
                Path,
                "is_dir",
                return_value=True,
            ),
            patch.object(
                Path,
                "is_symlink",
                side_effect=(
                    False,
                    True,
                ),
            ),
            patch.object(
                Path,
                "iterdir",
                return_value=iter((child,)),
            ),
            patch(f"{MODULE}.shutil.rmtree") as rmtree,
            patch.object(Path, "unlink") as unlink,
            patch(f"{MODULE}.provision_guest"),
        ):
            reset_guest()

        rmtree.assert_not_called()
        unlink.assert_called_once_with()

    def test_rejects_invalid_path_before_root_check(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.require_root") as require_root_call,
            self.assertRaisesRegex(
                TypeError,
                ("repository_root must be a string or Path"),
            ),
        ):
            reset_guest(
                repository_root=True,  # type: ignore[arg-type]
            )

        require_root_call.assert_not_called()

    def test_deletion_error_propagates(
        self,
    ) -> None:
        account = make_account()
        child = account.home / "curriculum"
        error = OSError("delete failed")

        with (
            patch(f"{MODULE}.require_root"),
            patch(
                f"{MODULE}.guest_account",
                return_value=account,
            ),
            patch.object(
                Path,
                "is_dir",
                return_value=True,
            ),
            patch.object(
                Path,
                "is_symlink",
                return_value=False,
            ),
            patch.object(
                Path,
                "iterdir",
                return_value=iter((child,)),
            ),
            patch(
                f"{MODULE}.shutil.rmtree",
                side_effect=error,
            ),
            patch(f"{MODULE}.provision_guest") as provision,
            self.assertRaises(OSError) as context,
        ):
            reset_guest()

        self.assertIs(
            context.exception,
            error,
        )
        provision.assert_not_called()


class GuestStatusTests(unittest.TestCase):
    def test_reports_complete_workspace(
        self,
    ) -> None:
        account = make_account()

        with (
            patch(
                f"{MODULE}.guest_account",
                return_value=account,
            ),
            patch(f"{MODULE}.account_ids") as account_ids,
            patch.object(
                Path,
                "is_dir",
                return_value=True,
            ),
        ):
            result = guest_status()

        account_ids.assert_called_once_with("guest")
        self.assertEqual(
            result,
            make_status(),
        )
        self.assertTrue(result.ok)

    def test_reports_partial_workspace(
        self,
    ) -> None:
        account = make_account()
        results = iter(
            (
                True,
                True,
                False,
                True,
            )
        )

        with (
            patch(
                f"{MODULE}.guest_account",
                return_value=account,
            ),
            patch(f"{MODULE}.account_ids"),
            patch.object(
                Path,
                "is_dir",
                side_effect=lambda: next(results),
            ),
        ):
            result = guest_status()

        self.assertTrue(result.account_exists)
        self.assertTrue(result.home_exists)
        self.assertTrue(result.curriculum_exists)
        self.assertFalse(result.media_exists)
        self.assertTrue(result.preferences_exist)
        self.assertFalse(result.ok)

    def test_lookup_error_returns_missing_status(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.guest_account",
            side_effect=LookupError("guest missing"),
        ):
            result = guest_status()

        self.assertEqual(
            result,
            make_status(
                account_exists=False,
                home_exists=False,
                curriculum_exists=False,
                media_exists=False,
                preferences_exist=False,
            ),
        )

    def test_account_id_error_returns_missing_status(
        self,
    ) -> None:
        account = make_account()

        with (
            patch(
                f"{MODULE}.guest_account",
                return_value=account,
            ),
            patch(
                f"{MODULE}.account_ids",
                side_effect=RuntimeError("account invalid"),
            ),
        ):
            result = guest_status()

        self.assertFalse(result.ok)
        self.assertFalse(result.account_exists)

    def test_filesystem_error_returns_missing_status(
        self,
    ) -> None:
        account = make_account()

        with (
            patch(
                f"{MODULE}.guest_account",
                return_value=account,
            ),
            patch(f"{MODULE}.account_ids"),
            patch.object(
                Path,
                "is_dir",
                side_effect=OSError("permission denied"),
            ),
        ):
            result = guest_status()

        self.assertFalse(result.ok)
        self.assertFalse(result.account_exists)

    def test_unexpected_error_propagates(
        self,
    ) -> None:
        error = ValueError("programming error")

        with (
            patch(
                f"{MODULE}.guest_account",
                side_effect=error,
            ),
            self.assertRaises(ValueError) as context,
        ):
            guest_status()

        self.assertIs(
            context.exception,
            error,
        )


class PrintStatusTests(unittest.TestCase):
    def test_prints_complete_status(self) -> None:
        status = make_status()

        with patch("builtins.print") as print_message:
            print_status(status)

        self.assertEqual(
            print_message.call_args_list,
            [
                call("Account:      OK"),
                call("Home:         OK"),
                call("Curriculum:   OK"),
                call("Media:        OK"),
                call("Preferences:  OK"),
            ],
        )

    def test_prints_missing_statuses(
        self,
    ) -> None:
        status = make_status(
            account_exists=False,
            curriculum_exists=False,
            preferences_exist=False,
        )

        with patch("builtins.print") as print_message:
            print_status(status)

        self.assertEqual(
            print_message.call_args_list,
            [
                call("Account:      Missing"),
                call("Home:         OK"),
                call("Curriculum:   Missing"),
                call("Media:        OK"),
                call("Preferences:  Missing"),
            ],
        )

    def test_rejects_invalid_status_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                ("status must be a GuestWorkspaceStatus"),
            ),
        ):
            print_status(
                object()  # type: ignore[arg-type]
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
            "betabox guest",
        )

    def test_parse_status(self) -> None:
        args = parse_args(
            [
                "status",
            ]
        )

        self.assertEqual(
            args.command,
            "status",
        )

    def test_parse_provision(self) -> None:
        args = parse_args(
            [
                "provision",
            ]
        )

        self.assertEqual(
            args.command,
            "provision",
        )

    def test_parse_reset(self) -> None:
        args = parse_args(
            [
                "reset",
            ]
        )

        self.assertEqual(
            args.command,
            "reset",
        )

    def test_no_command(self) -> None:
        args = parse_args([])

        self.assertIsNone(args.command)

    def test_rejects_unknown_command(
        self,
    ) -> None:
        with (
            patch("sys.stderr"),
            self.assertRaises(SystemExit),
        ):
            parse_args(
                [
                    "unknown",
                ]
            )


class MainTests(unittest.TestCase):
    def test_status_returns_zero_when_healthy(
        self,
    ) -> None:
        status = make_status()

        with (
            patch(f"{MODULE}._build_parser") as build_parser,
            patch(
                f"{MODULE}.guest_status",
                return_value=status,
            ) as get_status,
            patch(f"{MODULE}.print_status") as print_status_call,
        ):
            parser = build_parser.return_value
            parser.parse_args.return_value = argparse.Namespace(command="status")

            result = main(
                [
                    "status",
                ]
            )

        parser.parse_args.assert_called_once_with(
            [
                "status",
            ]
        )
        get_status.assert_called_once_with()
        print_status_call.assert_called_once_with(status)
        self.assertEqual(result, 0)

    def test_status_returns_one_when_incomplete(
        self,
    ) -> None:
        status = make_status(media_exists=False)

        with (
            patch(f"{MODULE}._build_parser") as build_parser,
            patch(
                f"{MODULE}.guest_status",
                return_value=status,
            ),
            patch(f"{MODULE}.print_status"),
        ):
            build_parser.return_value.parse_args.return_value = argparse.Namespace(
                command="status"
            )

            result = main([])

        self.assertEqual(result, 1)

    def test_provisions_guest(self) -> None:
        with (
            patch(f"{MODULE}._build_parser") as build_parser,
            patch(f"{MODULE}.require_root_or_elevate") as elevate,
            patch(f"{MODULE}.provision_guest") as provision,
            patch("builtins.print") as print_message,
        ):
            build_parser.return_value.parse_args.return_value = argparse.Namespace(
                command="provision"
            )

            result = main(
                [
                    "provision",
                ]
            )

        elevate.assert_called_once_with(
            [
                "guest",
                "provision",
            ]
        )
        provision.assert_called_once_with()
        print_message.assert_called_once_with("Guest workspace provisioned.")
        self.assertEqual(result, 0)

    def test_resets_guest(self) -> None:
        with (
            patch(f"{MODULE}._build_parser") as build_parser,
            patch(f"{MODULE}.require_root_or_elevate") as elevate,
            patch(f"{MODULE}.reset_guest") as reset,
            patch("builtins.print") as print_message,
        ):
            build_parser.return_value.parse_args.return_value = argparse.Namespace(
                command="reset"
            )

            result = main(
                [
                    "reset",
                ]
            )

        elevate.assert_called_once_with(
            [
                "guest",
                "reset",
            ]
        )
        reset.assert_called_once_with()
        print_message.assert_called_once_with("Guest workspace reset.")
        self.assertEqual(result, 0)

    def test_no_command_prints_help(self) -> None:
        with patch(f"{MODULE}._build_parser") as build_parser:
            parser = build_parser.return_value
            parser.parse_args.return_value = argparse.Namespace(command=None)

            result = main([])

        parser.print_help.assert_called_once_with()
        self.assertEqual(result, 1)

    def test_operational_error_is_reported(
        self,
    ) -> None:
        error = PermissionError("root required")

        with (
            patch(f"{MODULE}._build_parser") as build_parser,
            patch(
                f"{MODULE}.require_root_or_elevate",
                side_effect=error,
            ),
            patch(f"{MODULE}.provision_guest") as provision,
            patch(f"{MODULE}.sys.stderr") as stderr,
            patch("builtins.print") as print_message,
        ):
            build_parser.return_value.parse_args.return_value = argparse.Namespace(
                command="provision"
            )

            result = main([])

        self.assertEqual(result, 1)
        provision.assert_not_called()
        print_message.assert_called_once_with(
            ("Guest workspace operation failed: root required"),
            file=stderr,
        )

    def test_lookup_error_is_reported(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}._build_parser") as build_parser,
            patch(
                f"{MODULE}.guest_status",
                side_effect=LookupError("guest missing"),
            ),
            patch(f"{MODULE}.sys.stderr") as stderr,
            patch("builtins.print") as print_message,
        ):
            build_parser.return_value.parse_args.return_value = argparse.Namespace(
                command="status"
            )

            result = main([])

        self.assertEqual(result, 1)
        print_message.assert_called_once_with(
            ("Guest workspace operation failed: guest missing"),
            file=stderr,
        )

    def test_unexpected_error_propagates(
        self,
    ) -> None:
        error = AssertionError("programming error")

        with (
            patch(f"{MODULE}._build_parser") as build_parser,
            patch(
                f"{MODULE}.guest_status",
                side_effect=error,
            ),
            self.assertRaises(AssertionError) as context,
        ):
            build_parser.return_value.parse_args.return_value = argparse.Namespace(
                command="status"
            )

            main([])

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
