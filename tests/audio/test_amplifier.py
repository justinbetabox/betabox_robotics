from __future__ import annotations

import os
import subprocess
import unittest
from unittest.mock import call, patch

from betabox_robotics.audio.amplifier import (
    PIN_COMMAND_TIMEOUT,
    SPEAKER_ENABLE_GPIO,
    SPEAKER_WARMUP_SECONDS,
    SPEAKER_WARMUP_TIMEOUT,
    _environment_flag,
    _pin_commands,
    _run_command,
    _run_pin_tool,
    _validate_pin,
    _warm_up_speaker,
    disable_speaker,
    enable_speaker,
    speaker_on,
)


class ValidatePinTests(unittest.TestCase):
    def test_accepts_integer_pin(self) -> None:
        self.assertEqual(
            _validate_pin(20),
            20,
        )

    def test_accepts_zero_pin(self) -> None:
        self.assertEqual(
            _validate_pin(0),
            0,
        )

    def test_rejects_boolean_pin(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "pin must be an integer",
        ):
            _validate_pin(True)

    def test_rejects_non_integer_pin(self) -> None:
        for pin in (
            20.5,
            "20",
            None,
        ):
            with (
                self.subTest(pin=pin),
                self.assertRaisesRegex(
                    TypeError,
                    "pin must be an integer",
                ),
            ):
                _validate_pin(pin)

    def test_rejects_negative_pin(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "pin cannot be negative",
        ):
            _validate_pin(-1)


class EnvironmentFlagTests(unittest.TestCase):
    def test_returns_default_when_variable_is_missing(self) -> None:
        with patch.dict(
            os.environ,
            {},
            clear=True,
        ):
            self.assertTrue(
                _environment_flag(
                    "TEST_FLAG",
                    default=True,
                )
            )
            self.assertFalse(
                _environment_flag(
                    "TEST_FLAG",
                    default=False,
                )
            )

    def test_false_values_disable_flag(self) -> None:
        for value in (
            "0",
            "false",
            "False",
            "FALSE",
            "no",
            "NO",
            "off",
            "OFF",
            " false ",
        ):
            with (
                self.subTest(value=value),
                patch.dict(
                    os.environ,
                    {
                        "TEST_FLAG": value,
                    },
                    clear=True,
                ),
            ):
                self.assertFalse(
                    _environment_flag(
                        "TEST_FLAG",
                        default=True,
                    )
                )

    def test_other_values_enable_flag(self) -> None:
        for value in (
            "1",
            "true",
            "yes",
            "on",
            "enabled",
            "",
        ):
            with (
                self.subTest(value=value),
                patch.dict(
                    os.environ,
                    {
                        "TEST_FLAG": value,
                    },
                    clear=True,
                ),
            ):
                self.assertTrue(
                    _environment_flag(
                        "TEST_FLAG",
                        default=False,
                    )
                )


class PinCommandsTests(unittest.TestCase):
    def test_returns_both_available_commands_for_high(self) -> None:
        def which(command: str) -> str | None:
            paths = {
                "pinctrl": "/usr/bin/pinctrl",
                "raspi-gpio": "/usr/bin/raspi-gpio",
            }
            return paths.get(command)

        with patch(
            "betabox_robotics.audio.amplifier.shutil.which",
            side_effect=which,
        ):
            commands = _pin_commands(
                20,
                high=True,
            )

        self.assertEqual(
            commands,
            (
                (
                    "/usr/bin/pinctrl",
                    "set",
                    "20",
                    "op",
                    "dh",
                ),
                (
                    "/usr/bin/raspi-gpio",
                    "set",
                    "20",
                    "op",
                    "dh",
                ),
            ),
        )

    def test_returns_low_commands(self) -> None:
        with patch(
            "betabox_robotics.audio.amplifier.shutil.which",
            side_effect=lambda command: (
                "/usr/bin/pinctrl" if command == "pinctrl" else None
            ),
        ):
            commands = _pin_commands(
                20,
                high=False,
            )

        self.assertEqual(
            commands,
            (
                (
                    "/usr/bin/pinctrl",
                    "set",
                    "20",
                    "op",
                    "dl",
                ),
            ),
        )

    def test_omits_unavailable_tools(self) -> None:
        with patch(
            "betabox_robotics.audio.amplifier.shutil.which",
            return_value=None,
        ):
            self.assertEqual(
                _pin_commands(
                    20,
                    high=True,
                ),
                (),
            )


class RunCommandTests(unittest.TestCase):
    def test_returns_true_for_success(self) -> None:
        completed = subprocess.CompletedProcess(
            args=("command",),
            returncode=0,
        )

        with patch(
            "betabox_robotics.audio.amplifier.subprocess.run",
            return_value=completed,
        ) as run:
            result = _run_command(
                (
                    "command",
                    "argument",
                ),
                timeout=1.5,
            )

        self.assertTrue(result)

        run.assert_called_once_with(
            (
                "command",
                "argument",
            ),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=1.5,
        )

    def test_returns_false_for_nonzero_exit(self) -> None:
        completed = subprocess.CompletedProcess(
            args=("command",),
            returncode=1,
        )

        with patch(
            "betabox_robotics.audio.amplifier.subprocess.run",
            return_value=completed,
        ):
            self.assertFalse(
                _run_command(
                    ("command",),
                    timeout=1.0,
                )
            )

    def test_returns_false_for_os_error(self) -> None:
        with patch(
            "betabox_robotics.audio.amplifier.subprocess.run",
            side_effect=OSError("could not launch"),
        ):
            self.assertFalse(
                _run_command(
                    ("command",),
                    timeout=1.0,
                )
            )

    def test_returns_false_for_timeout(self) -> None:
        with patch(
            "betabox_robotics.audio.amplifier.subprocess.run",
            side_effect=subprocess.TimeoutExpired(
                cmd=("command",),
                timeout=1.0,
            ),
        ):
            self.assertFalse(
                _run_command(
                    ("command",),
                    timeout=1.0,
                )
            )


class RunPinToolTests(unittest.TestCase):
    def test_returns_false_when_no_tool_is_available(self) -> None:
        with (
            patch(
                "betabox_robotics.audio.amplifier._pin_commands",
                return_value=(),
            ),
            patch(
                "betabox_robotics.audio.amplifier._run_command",
            ) as run_command,
        ):
            self.assertFalse(
                _run_pin_tool(
                    20,
                    high=True,
                )
            )

        run_command.assert_not_called()

    def test_runs_directly_as_root(self) -> None:
        command = (
            "/usr/bin/pinctrl",
            "set",
            "20",
            "op",
            "dh",
        )

        with (
            patch(
                "betabox_robotics.audio.amplifier._pin_commands",
                return_value=(command,),
            ),
            patch(
                "betabox_robotics.audio.amplifier.os.geteuid",
                return_value=0,
            ),
            patch(
                "betabox_robotics.audio.amplifier._run_command",
                return_value=True,
            ) as run_command,
        ):
            result = _run_pin_tool(
                20,
                high=True,
            )

        self.assertTrue(result)

        run_command.assert_called_once_with(
            command,
            timeout=PIN_COMMAND_TIMEOUT,
        )

    def test_uses_sudo_for_non_root_by_default(self) -> None:
        command = (
            "/usr/bin/pinctrl",
            "set",
            "20",
            "op",
            "dh",
        )

        with (
            patch.dict(
                os.environ,
                {},
                clear=True,
            ),
            patch(
                "betabox_robotics.audio.amplifier._pin_commands",
                return_value=(command,),
            ),
            patch(
                "betabox_robotics.audio.amplifier.os.geteuid",
                return_value=1000,
            ),
            patch(
                "betabox_robotics.audio.amplifier._run_command",
                return_value=True,
            ) as run_command,
        ):
            result = _run_pin_tool(
                20,
                high=True,
            )

        self.assertTrue(result)

        run_command.assert_called_once_with(
            (
                "sudo",
                "-n",
                *command,
            ),
            timeout=PIN_COMMAND_TIMEOUT,
        )

    def test_does_not_use_sudo_when_disabled(self) -> None:
        command = (
            "/usr/bin/pinctrl",
            "set",
            "20",
            "op",
            "dh",
        )

        with (
            patch.dict(
                os.environ,
                {
                    "BETABOX_AUDIO_SUDO": "0",
                },
                clear=True,
            ),
            patch(
                "betabox_robotics.audio.amplifier._pin_commands",
                return_value=(command,),
            ),
            patch(
                "betabox_robotics.audio.amplifier.os.geteuid",
                return_value=1000,
            ),
            patch(
                "betabox_robotics.audio.amplifier._run_command",
                return_value=True,
            ) as run_command,
        ):
            result = _run_pin_tool(
                20,
                high=True,
            )

        self.assertTrue(result)

        run_command.assert_called_once_with(
            command,
            timeout=PIN_COMMAND_TIMEOUT,
        )

    def test_falls_back_to_second_command(self) -> None:
        first = (
            "/usr/bin/pinctrl",
            "set",
            "20",
            "op",
            "dh",
        )
        second = (
            "/usr/bin/raspi-gpio",
            "set",
            "20",
            "op",
            "dh",
        )

        with (
            patch(
                "betabox_robotics.audio.amplifier._pin_commands",
                return_value=(
                    first,
                    second,
                ),
            ),
            patch(
                "betabox_robotics.audio.amplifier.os.geteuid",
                return_value=0,
            ),
            patch(
                "betabox_robotics.audio.amplifier._run_command",
                side_effect=(
                    False,
                    True,
                ),
            ) as run_command,
        ):
            result = _run_pin_tool(
                20,
                high=True,
            )

        self.assertTrue(result)

        self.assertEqual(
            run_command.call_args_list,
            [
                call(
                    first,
                    timeout=PIN_COMMAND_TIMEOUT,
                ),
                call(
                    second,
                    timeout=PIN_COMMAND_TIMEOUT,
                ),
            ],
        )

    def test_stops_after_first_success(self) -> None:
        first = (
            "/usr/bin/pinctrl",
            "set",
            "20",
            "op",
            "dh",
        )
        second = (
            "/usr/bin/raspi-gpio",
            "set",
            "20",
            "op",
            "dh",
        )

        with (
            patch(
                "betabox_robotics.audio.amplifier._pin_commands",
                return_value=(
                    first,
                    second,
                ),
            ),
            patch(
                "betabox_robotics.audio.amplifier.os.geteuid",
                return_value=0,
            ),
            patch(
                "betabox_robotics.audio.amplifier._run_command",
                return_value=True,
            ) as run_command,
        ):
            result = _run_pin_tool(
                20,
                high=True,
            )

        self.assertTrue(result)

        run_command.assert_called_once_with(
            first,
            timeout=PIN_COMMAND_TIMEOUT,
        )

    def test_returns_false_when_all_commands_fail(self) -> None:
        commands = (
            (
                "/usr/bin/pinctrl",
                "set",
                "20",
                "op",
                "dh",
            ),
            (
                "/usr/bin/raspi-gpio",
                "set",
                "20",
                "op",
                "dh",
            ),
        )

        with (
            patch(
                "betabox_robotics.audio.amplifier._pin_commands",
                return_value=commands,
            ),
            patch(
                "betabox_robotics.audio.amplifier.os.geteuid",
                return_value=0,
            ),
            patch(
                "betabox_robotics.audio.amplifier._run_command",
                return_value=False,
            ) as run_command,
        ):
            result = _run_pin_tool(
                20,
                high=True,
            )

        self.assertFalse(result)
        self.assertEqual(
            run_command.call_count,
            2,
        )

    def test_validates_pin_before_discovering_commands(self) -> None:
        with (
            patch(
                "betabox_robotics.audio.amplifier._pin_commands",
            ) as pin_commands,
            self.assertRaisesRegex(
                TypeError,
                "pin must be an integer",
            ),
        ):
            _run_pin_tool(
                True,
                high=True,
            )

        pin_commands.assert_not_called()


class WarmUpSpeakerTests(unittest.TestCase):
    def test_does_nothing_when_play_is_unavailable(self) -> None:
        with (
            patch(
                "betabox_robotics.audio.amplifier.shutil.which",
                return_value=None,
            ),
            patch(
                "betabox_robotics.audio.amplifier._run_command",
            ) as run_command,
        ):
            _warm_up_speaker()

        run_command.assert_not_called()

    def test_runs_sox_warmup(self) -> None:
        with (
            patch(
                "betabox_robotics.audio.amplifier.shutil.which",
                return_value="/usr/bin/play",
            ),
            patch(
                "betabox_robotics.audio.amplifier._run_command",
                return_value=True,
            ) as run_command,
        ):
            _warm_up_speaker()

        run_command.assert_called_once_with(
            (
                "/usr/bin/play",
                "-n",
                "trim",
                "0.0",
                str(SPEAKER_WARMUP_SECONDS),
            ),
            timeout=SPEAKER_WARMUP_TIMEOUT,
        )


class SpeakerControlTests(unittest.TestCase):
    def test_enable_uses_default_pin(self) -> None:
        with (
            patch(
                "betabox_robotics.audio.amplifier._run_pin_tool",
                return_value=True,
            ) as run_pin_tool,
            patch(
                "betabox_robotics.audio.amplifier._warm_up_speaker",
            ) as warm_up,
        ):
            result = enable_speaker()

        self.assertTrue(result)

        run_pin_tool.assert_called_once_with(
            SPEAKER_ENABLE_GPIO,
            high=True,
        )
        warm_up.assert_called_once_with()

    def test_enable_uses_custom_pin(self) -> None:
        with (
            patch(
                "betabox_robotics.audio.amplifier._run_pin_tool",
                return_value=True,
            ) as run_pin_tool,
            patch(
                "betabox_robotics.audio.amplifier._warm_up_speaker",
            ),
        ):
            result = enable_speaker(21)

        self.assertTrue(result)

        run_pin_tool.assert_called_once_with(
            21,
            high=True,
        )

    def test_enable_does_not_warm_up_after_failure(self) -> None:
        with (
            patch(
                "betabox_robotics.audio.amplifier._run_pin_tool",
                return_value=False,
            ),
            patch(
                "betabox_robotics.audio.amplifier._warm_up_speaker",
            ) as warm_up,
        ):
            result = enable_speaker()

        self.assertFalse(result)
        warm_up.assert_not_called()

    def test_warmup_failure_does_not_change_enable_result(self) -> None:
        with (
            patch(
                "betabox_robotics.audio.amplifier._run_pin_tool",
                return_value=True,
            ),
            patch(
                "betabox_robotics.audio.amplifier._warm_up_speaker",
                return_value=None,
            ),
        ):
            self.assertTrue(enable_speaker())

    def test_disable_requests_low_output(self) -> None:
        with patch(
            "betabox_robotics.audio.amplifier._run_pin_tool",
            return_value=True,
        ) as run_pin_tool:
            result = disable_speaker(21)

        self.assertTrue(result)

        run_pin_tool.assert_called_once_with(
            21,
            high=False,
        )


class SpeakerContextTests(unittest.TestCase):
    def test_yields_enable_result(self) -> None:
        with (
            patch(
                "betabox_robotics.audio.amplifier.enable_speaker",
                return_value=True,
            ) as enable,
            patch(
                "betabox_robotics.audio.amplifier.disable_speaker",
                return_value=True,
            ) as disable,
            speaker_on(21) as enabled,
        ):
            self.assertTrue(enabled)

        enable.assert_called_once_with(21)
        disable.assert_called_once_with(21)

    def test_yields_false_when_enable_fails(self) -> None:
        with (
            patch(
                "betabox_robotics.audio.amplifier.enable_speaker",
                return_value=False,
            ),
            patch(
                "betabox_robotics.audio.amplifier.disable_speaker",
                return_value=True,
            ) as disable,
            speaker_on() as enabled,
        ):
            self.assertFalse(enabled)

        disable.assert_called_once_with(SPEAKER_ENABLE_GPIO)

    def test_disables_after_body_exception(self) -> None:
        with (
            patch(
                "betabox_robotics.audio.amplifier.enable_speaker",
                return_value=True,
            ),
            patch(
                "betabox_robotics.audio.amplifier.disable_speaker",
                return_value=True,
            ) as disable,
            self.assertRaisesRegex(
                RuntimeError,
                "body failed",
            ),
            speaker_on(21),
        ):
            raise RuntimeError("body failed")

        disable.assert_called_once_with(21)

    def test_disable_error_propagates_on_normal_exit(self) -> None:
        with (
            patch(
                "betabox_robotics.audio.amplifier.enable_speaker",
                return_value=True,
            ),
            patch(
                "betabox_robotics.audio.amplifier.disable_speaker",
                side_effect=OSError("disable failed"),
            ),
            self.assertRaisesRegex(
                OSError,
                "disable failed",
            ),
            speaker_on(),
        ):
            pass


if __name__ == "__main__":
    unittest.main()
