from __future__ import annotations

import argparse
import unittest
from unittest.mock import Mock, patch

from betabox_robotics.cli.betabox import (
    COMMANDS,
    _build_parser,
    _without_args,
    main,
    parse_args,
)

MODULE = "betabox_robotics.cli.betabox"


class WithoutArgsTests(unittest.TestCase):
    def test_calls_wrapped_handler_without_arguments(self) -> None:
        handler = Mock(return_value=7)
        wrapped = _without_args(handler)

        self.assertEqual(wrapped(), 7)
        handler.assert_called_once_with()

    def test_accepts_none_and_empty_arguments(self) -> None:
        for argv in (None, []):
            with self.subTest(argv=argv):
                handler = Mock(return_value=0)
                wrapped = _without_args(handler)

                self.assertEqual(wrapped(argv), 0)
                handler.assert_called_once_with()

    def test_rejects_nonempty_arguments_before_handler(self) -> None:
        handler = Mock()
        wrapped = _without_args(handler)

        with self.assertRaisesRegex(
            ValueError,
            "command does not accept arguments",
        ):
            wrapped(["--unexpected"])

        handler.assert_not_called()

    def test_unexpected_handler_error_propagates(self) -> None:
        error = RuntimeError("handler failed")
        wrapped = _without_args(Mock(side_effect=error))

        with self.assertRaises(RuntimeError) as context:
            wrapped([])

        self.assertIs(context.exception, error)


class CommandsTests(unittest.TestCase):
    def test_contains_expected_commands(self) -> None:
        self.assertEqual(
            set(COMMANDS),
            {
                "install-check",
                "verify",
                "status",
                "boot-announce",
                "monitor",
                "services",
                "events",
                "logs",
                "doctor",
                "backup",
                "snapshot",
                "restore",
                "reset",
                "guest",
                "set-hostname",
                "wifi-fallback",
                "video",
                "launchpad",
            },
        )

    def test_each_command_has_help_and_callable_handler(self) -> None:
        for name, (help_text, handler) in COMMANDS.items():
            with self.subTest(command=name):
                self.assertIsInstance(help_text, str)
                self.assertTrue(help_text.strip())
                self.assertTrue(callable(handler))


class BuildParserTests(unittest.TestCase):
    def test_builds_parser(self) -> None:
        parser = _build_parser()

        self.assertIsInstance(parser, argparse.ArgumentParser)
        self.assertEqual(parser.prog, "betabox")

    def test_accepts_each_registered_command(self) -> None:
        parser = _build_parser()

        for name in COMMANDS:
            with self.subTest(command=name):
                args, extra = parser.parse_known_args([name])
                self.assertEqual(args.command, name)
                self.assertEqual(extra, [])

    def test_forwards_subcommand_arguments(self) -> None:
        parser = _build_parser()

        args, extra = parser.parse_known_args(
            ["snapshot", "--name", "classroom", "--other"]
        )

        self.assertEqual(args.command, "snapshot")
        self.assertEqual(extra, ["--name", "classroom", "--other"])

    def test_forwards_subcommand_help(self) -> None:
        parser = _build_parser()

        args, extra = parser.parse_known_args(["status", "--help"])

        self.assertEqual(args.command, "status")
        self.assertEqual(extra, ["--help"])

    def test_no_command_returns_none(self) -> None:
        args, extra = _build_parser().parse_known_args([])

        self.assertIsNone(args.command)
        self.assertEqual(extra, [])

    def test_unknown_command_is_rejected(self) -> None:
        with (
            patch("sys.stderr"),
            self.assertRaises(SystemExit),
        ):
            _build_parser().parse_known_args(["unknown"])


class ParseArgsTests(unittest.TestCase):
    def test_returns_namespace_and_extra_arguments(self) -> None:
        args, extra = parse_args(
            ["logs", "monitor", "--lines", "20"]
        )

        self.assertEqual(args.command, "logs")
        self.assertEqual(extra, ["monitor", "--lines", "20"])

    def test_defaults_to_no_command(self) -> None:
        args, extra = parse_args([])

        self.assertIsNone(args.command)
        self.assertEqual(extra, [])

    def test_uses_build_parser(self) -> None:
        parser = Mock(spec=argparse.ArgumentParser)
        parser.parse_known_args.return_value = (
            argparse.Namespace(command="status"),
            ["--json"],
        )

        with patch(
            f"{MODULE}._build_parser",
            return_value=parser,
        ) as build:
            result = parse_args(["status", "--json"])

        build.assert_called_once_with()
        parser.parse_known_args.assert_called_once_with(
            ["status", "--json"]
        )
        self.assertEqual(
            result,
            (
                argparse.Namespace(command="status"),
                ["--json"],
            ),
        )


class MainTests(unittest.TestCase):
    def test_dispatches_command_with_extra_arguments(self) -> None:
        handler = Mock(return_value=0)
        parser = Mock(spec=argparse.ArgumentParser)
        parser.parse_known_args.return_value = (
            argparse.Namespace(command="snapshot"),
            ["--name", "classroom"],
        )

        with (
            patch(
                f"{MODULE}._build_parser",
                return_value=parser,
            ),
            patch.dict(
                COMMANDS,
                {
                    "snapshot": (
                        "Create snapshot",
                        handler,
                    )
                },
                clear=True,
            ),
        ):
            result = main(
                ["snapshot", "--name", "classroom"]
            )

        self.assertEqual(result, 0)
        handler.assert_called_once_with(
            ["--name", "classroom"]
        )
        parser.print_help.assert_not_called()

    def test_returns_handler_exit_code(self) -> None:
        handler = Mock(return_value=7)
        parser = Mock(spec=argparse.ArgumentParser)
        parser.parse_known_args.return_value = (
            argparse.Namespace(command="doctor"),
            [],
        )

        with (
            patch(
                f"{MODULE}._build_parser",
                return_value=parser,
            ),
            patch.dict(
                COMMANDS,
                {"doctor": ("Run doctor", handler)},
                clear=True,
            ),
        ):
            result = main(["doctor"])

        self.assertEqual(result, 7)

    def test_no_command_prints_help_and_returns_one(self) -> None:
        parser = Mock(spec=argparse.ArgumentParser)
        parser.parse_known_args.return_value = (
            argparse.Namespace(command=None),
            [],
        )

        with patch(
            f"{MODULE}._build_parser",
            return_value=parser,
        ):
            result = main([])

        self.assertEqual(result, 1)
        parser.print_help.assert_called_once_with()

    def test_missing_registry_command_prints_help(self) -> None:
        parser = Mock(spec=argparse.ArgumentParser)
        parser.parse_known_args.return_value = (
            argparse.Namespace(command="missing"),
            [],
        )

        with (
            patch(
                f"{MODULE}._build_parser",
                return_value=parser,
            ),
            patch.dict(COMMANDS, {}, clear=True),
        ):
            result = main(["missing"])

        self.assertEqual(result, 1)
        parser.print_help.assert_called_once_with()

    def test_value_error_is_reported(self) -> None:
        handler = Mock(
            side_effect=ValueError("invalid arguments")
        )
        parser = Mock(spec=argparse.ArgumentParser)
        parser.parse_known_args.return_value = (
            argparse.Namespace(command="verify"),
            ["--unexpected"],
        )

        with (
            patch(
                f"{MODULE}._build_parser",
                return_value=parser,
            ),
            patch.dict(
                COMMANDS,
                {"verify": ("Run verification", handler)},
                clear=True,
            ),
            patch("builtins.print") as print_message,
        ):
            result = main(["verify", "--unexpected"])

        self.assertEqual(result, 1)
        print_message.assert_called_once_with(
            "betabox verify failed: invalid arguments"
        )

    def test_type_error_is_reported(self) -> None:
        handler = Mock(side_effect=TypeError("invalid value"))
        parser = Mock(spec=argparse.ArgumentParser)
        parser.parse_known_args.return_value = (
            argparse.Namespace(command="status"),
            [],
        )

        with (
            patch(
                f"{MODULE}._build_parser",
                return_value=parser,
            ),
            patch.dict(
                COMMANDS,
                {"status": ("Show status", handler)},
                clear=True,
            ),
            patch("builtins.print") as print_message,
        ):
            result = main(["status"])

        self.assertEqual(result, 1)
        print_message.assert_called_once_with(
            "betabox status failed: invalid value"
        )

    def test_unexpected_error_propagates(self) -> None:
        error = RuntimeError("programming error")
        handler = Mock(side_effect=error)
        parser = Mock(spec=argparse.ArgumentParser)
        parser.parse_known_args.return_value = (
            argparse.Namespace(command="status"),
            [],
        )

        with (
            patch(
                f"{MODULE}._build_parser",
                return_value=parser,
            ),
            patch.dict(
                COMMANDS,
                {"status": ("Show status", handler)},
                clear=True,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            main(["status"])

        self.assertIs(context.exception, error)

    def test_wrapped_no_argument_command_rejects_extra(self) -> None:
        handler = Mock(return_value=0)
        wrapped = _without_args(handler)
        parser = Mock(spec=argparse.ArgumentParser)
        parser.parse_known_args.return_value = (
            argparse.Namespace(command="verify"),
            ["--unexpected"],
        )

        with (
            patch(
                f"{MODULE}._build_parser",
                return_value=parser,
            ),
            patch.dict(
                COMMANDS,
                {"verify": ("Run verification", wrapped)},
                clear=True,
            ),
            patch("builtins.print") as print_message,
        ):
            result = main(["verify", "--unexpected"])

        self.assertEqual(result, 1)
        handler.assert_not_called()
        print_message.assert_called_once_with(
            "betabox verify failed: command does not accept arguments"
        )


class InitExportsTests(unittest.TestCase):
    def test_cli_package_exports_main(self) -> None:
        from betabox_robotics import cli

        self.assertIs(cli.main, main)

    def test_cli_all_contains_main(self) -> None:
        from betabox_robotics import cli

        self.assertEqual(cli.__all__, ["main"])


if __name__ == "__main__":
    unittest.main()
