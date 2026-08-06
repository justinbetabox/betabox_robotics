from __future__ import annotations

import json
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, mock_open, patch

from betabox_robotics.audio import Audio
from betabox_robotics.audio.exceptions import AudioError
from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.boot_announce import (
    FAILURE_ANNOUNCEMENTS,
    _validate_audio,
    _validate_config,
    _validate_string,
    announce_failures,
    close_audio,
    log,
    main,
    say,
    summarize_checks,
)

MODULE = "betabox_robotics.services.boot_announce"


def make_config(
    *,
    state_dir: Path,
    boot_announce_log: Path,
):
    paths = replace(
        DEFAULT_PLATFORM_CONFIG.paths,
        state_dir=state_dir,
        boot_announce_log=boot_announce_log,
    )

    return replace(
        DEFAULT_PLATFORM_CONFIG,
        paths=paths,
    )


def make_audio() -> Audio:
    """
    Create an Audio instance without opening hardware.

    Tests patch the methods that would otherwise interact
    with audio hardware or subprocesses.
    """

    return object.__new__(Audio)


def make_check(
    name: str,
    ok: bool,
) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        ok=ok,
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
            " Ready for class ",
            name="message",
        )

        self.assertEqual(
            result,
            "Ready for class",
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
                    "message must be a string",
                ),
            ):
                _validate_string(
                    value,
                    name="message",
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
                    "message cannot be empty",
                ),
            ):
                _validate_string(
                    value,
                    name="message",
                )

    def test_validate_audio_accepts_audio(
        self,
    ) -> None:
        audio = make_audio()

        result = _validate_audio(audio)

        self.assertIs(
            result,
            audio,
        )

    def test_validate_audio_rejects_invalid_value(
        self,
    ) -> None:
        for value in (
            None,
            object(),
            "audio",
            123,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "audio must be an Audio",
                ),
            ):
                _validate_audio(value)


class LogTests(unittest.TestCase):
    def test_creates_state_directory_and_appends_log(
        self,
    ) -> None:
        file_handle = mock_open()

        with (
            patch.object(
                Path,
                "mkdir",
            ) as mkdir,
            patch.object(
                Path,
                "open",
                file_handle,
            ) as open_file,
            patch(
                f"{MODULE}.time.strftime",
                return_value=("2026-08-05 18:03:00"),
            ) as strftime,
        ):
            log(" Boot announcer started ")

        mkdir.assert_called_once_with(
            parents=True,
            exist_ok=True,
        )
        open_file.assert_called_once_with(
            "a",
            encoding="utf-8",
        )
        file_handle().write.assert_called_once_with(
            "2026-08-05 18:03:00 Boot announcer started\n"
        )
        strftime.assert_called_once_with("%Y-%m-%d %H:%M:%S")

    def test_repeated_calls_append_entries(
        self,
    ) -> None:
        file_handle = mock_open()

        with (
            patch.object(
                Path,
                "mkdir",
            ) as mkdir,
            patch.object(
                Path,
                "open",
                file_handle,
            ) as open_file,
            patch(
                f"{MODULE}.time.strftime",
                side_effect=(
                    "2026-08-05 18:03:00",
                    "2026-08-05 18:04:00",
                ),
            ),
        ):
            log("first entry")
            log("second entry")

        self.assertEqual(
            mkdir.call_count,
            2,
        )
        self.assertEqual(
            open_file.call_args_list,
            [
                call(
                    "a",
                    encoding="utf-8",
                ),
                call(
                    "a",
                    encoding="utf-8",
                ),
            ],
        )
        self.assertEqual(
            file_handle().write.call_args_list,
            [
                call("2026-08-05 18:03:00 first entry\n"),
                call("2026-08-05 18:04:00 second entry\n"),
            ],
        )

    def test_uses_append_mode_and_utf8(
        self,
    ) -> None:
        file_handle = mock_open()

        with (
            patch.object(Path, "mkdir") as mkdir,
            patch.object(
                Path,
                "open",
                file_handle,
            ) as open_file,
            patch(
                f"{MODULE}.time.strftime",
                return_value=("2026-08-05 18:03:00"),
            ),
        ):
            log("message")

        mkdir.assert_called_once_with(
            parents=True,
            exist_ok=True,
        )
        open_file.assert_called_once_with(
            "a",
            encoding="utf-8",
        )
        file_handle().write.assert_called_once_with("2026-08-05 18:03:00 message\n")

    def test_rejects_invalid_message_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "mkdir") as mkdir,
            self.assertRaisesRegex(
                TypeError,
                "message must be a string",
            ),
        ):
            log(
                None  # type: ignore[arg-type]
            )

        mkdir.assert_not_called()

    def test_rejects_empty_message_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "mkdir") as mkdir,
            self.assertRaisesRegex(
                ValueError,
                "message cannot be empty",
            ),
        ):
            log(" ")

        mkdir.assert_not_called()

    def test_rejects_invalid_config_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "mkdir") as mkdir,
            self.assertRaisesRegex(
                TypeError,
                ("config must be a PlatformConfig"),
            ),
        ):
            log(
                "message",
                object(),  # type: ignore[arg-type]
            )

        mkdir.assert_not_called()

    def test_filesystem_error_propagates(
        self,
    ) -> None:
        error = OSError("permission denied")

        with (
            patch.object(
                Path,
                "mkdir",
                side_effect=error,
            ),
            self.assertRaises(OSError) as context,
        ):
            log("message")

        self.assertIs(
            context.exception,
            error,
        )


class SayTests(unittest.TestCase):
    def test_logs_and_speaks_message(
        self,
    ) -> None:
        audio = make_audio()

        with (
            patch(f"{MODULE}.log") as log_message,
            patch.object(
                Audio,
                "say",
                return_value=None,
            ) as audio_say,
        ):
            result = say(
                audio,
                " Ready for class ",
            )

        self.assertTrue(result)
        log_message.assert_called_once_with(
            "SAY: Ready for class",
            DEFAULT_PLATFORM_CONFIG,
        )
        audio_say.assert_called_once_with("Ready for class")

    def test_audio_error_is_logged(
        self,
    ) -> None:
        audio = make_audio()
        error = AudioError("speech failed")

        with (
            patch(f"{MODULE}.log") as log_message,
            patch.object(
                Audio,
                "say",
                side_effect=error,
            ),
        ):
            result = say(
                audio,
                "Ready for class",
            )

        self.assertFalse(result)
        self.assertEqual(
            log_message.call_args_list,
            [
                call(
                    "SAY: Ready for class",
                    DEFAULT_PLATFORM_CONFIG,
                ),
                call(
                    "audio failed: speech failed",
                    DEFAULT_PLATFORM_CONFIG,
                ),
            ],
        )

    def test_rejects_invalid_audio_before_logging(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.log") as log_message,
            self.assertRaisesRegex(
                TypeError,
                "audio must be an Audio",
            ),
        ):
            say(
                object(),  # type: ignore[arg-type]
                "message",
            )

        log_message.assert_not_called()

    def test_rejects_invalid_message_before_logging(
        self,
    ) -> None:
        audio = make_audio()

        with (
            patch(f"{MODULE}.log") as log_message,
            self.assertRaisesRegex(
                ValueError,
                "message cannot be empty",
            ),
        ):
            say(
                audio,
                " ",
            )

        log_message.assert_not_called()

    def test_unexpected_audio_error_propagates(
        self,
    ) -> None:
        audio = make_audio()
        error = RuntimeError("programming error")

        with (
            patch(f"{MODULE}.log"),
            patch.object(
                Audio,
                "say",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            say(
                audio,
                "message",
            )

        self.assertIs(
            context.exception,
            error,
        )


class SummarizeChecksTests(unittest.TestCase):
    def test_returns_ready_when_all_checks_pass(
        self,
    ) -> None:
        checks = (
            make_check(
                "hardware:i2c",
                True,
            ),
            make_check(
                "camera:picamera2",
                True,
            ),
        )

        with (
            patch(
                f"{MODULE}.collect_checks",
                return_value=checks,
            ) as collect,
            patch(f"{MODULE}.log") as log_message,
        ):
            ready, results = summarize_checks()

        self.assertTrue(ready)
        self.assertEqual(
            results,
            {
                "hardware:i2c": True,
                "camera:picamera2": True,
            },
        )
        collect.assert_called_once_with(
            include_robot=True,
            config=DEFAULT_PLATFORM_CONFIG,
        )
        log_message.assert_called_once_with(
            (
                "Verification results: "
                + json.dumps(
                    results,
                    sort_keys=True,
                )
            ),
            DEFAULT_PLATFORM_CONFIG,
        )

    def test_returns_not_ready_when_check_fails(
        self,
    ) -> None:
        checks = (
            make_check(
                "hardware:i2c",
                True,
            ),
            make_check(
                "camera:picamera2",
                False,
            ),
        )

        with (
            patch(
                f"{MODULE}.collect_checks",
                return_value=checks,
            ),
            patch(f"{MODULE}.log"),
        ):
            ready, results = summarize_checks()

        self.assertFalse(ready)
        self.assertFalse(results["camera:picamera2"])

    def test_empty_checks_are_not_ready(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.collect_checks",
                return_value=(),
            ),
            patch(f"{MODULE}.log"),
        ):
            ready, results = summarize_checks()

        self.assertFalse(ready)
        self.assertEqual(
            results,
            {},
        )

    def test_duplicate_names_use_last_result(
        self,
    ) -> None:
        checks = (
            make_check(
                "hardware:i2c",
                False,
            ),
            make_check(
                "hardware:i2c",
                True,
            ),
        )

        with (
            patch(
                f"{MODULE}.collect_checks",
                return_value=checks,
            ),
            patch(f"{MODULE}.log"),
        ):
            ready, results = summarize_checks()

        self.assertTrue(ready)
        self.assertEqual(
            results,
            {
                "hardware:i2c": True,
            },
        )

    def test_rejects_invalid_config_before_collection(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.collect_checks") as collect,
            self.assertRaisesRegex(
                TypeError,
                ("config must be a PlatformConfig"),
            ),
        ):
            summarize_checks(
                object()  # type: ignore[arg-type]
            )

        collect.assert_not_called()

    def test_collection_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("verification failed")

        with (
            patch(
                f"{MODULE}.collect_checks",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            summarize_checks()

        self.assertIs(
            context.exception,
            error,
        )


class AnnounceFailuresTests(unittest.TestCase):
    def test_announces_each_failed_known_check(
        self,
    ) -> None:
        audio = make_audio()
        results = {name: False for name, _ in (FAILURE_ANNOUNCEMENTS)}

        with patch(
            f"{MODULE}.say",
            return_value=True,
        ) as say_message:
            announce_failures(
                audio,
                results,
            )

        self.assertEqual(
            say_message.call_args_list,
            [
                call(
                    audio,
                    message,
                    DEFAULT_PLATFORM_CONFIG,
                )
                for _, message in (FAILURE_ANNOUNCEMENTS)
            ],
        )

    def test_skips_passing_checks(
        self,
    ) -> None:
        audio = make_audio()
        results = {name: True for name, _ in (FAILURE_ANNOUNCEMENTS)}

        with patch(f"{MODULE}.say") as say_message:
            announce_failures(
                audio,
                results,
            )

        say_message.assert_not_called()

    def test_missing_known_check_is_announced_as_failure(
        self,
    ) -> None:
        audio = make_audio()

        with patch(
            f"{MODULE}.say",
            return_value=True,
        ) as say_message:
            announce_failures(
                audio,
                {},
            )

        self.assertEqual(
            say_message.call_count,
            len(FAILURE_ANNOUNCEMENTS),
        )

    def test_unknown_results_are_ignored(
        self,
    ) -> None:
        audio = make_audio()
        results = {
            "unknown:check": False,
            **{name: True for name, _ in (FAILURE_ANNOUNCEMENTS)},
        }

        with patch(f"{MODULE}.say") as say_message:
            announce_failures(
                audio,
                results,
            )

        say_message.assert_not_called()

    def test_rejects_invalid_audio_before_results(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "audio must be an Audio",
        ):
            announce_failures(
                object(),  # type: ignore[arg-type]
                {},
            )

    def test_rejects_non_dictionary_results(
        self,
    ) -> None:
        audio = make_audio()

        with self.assertRaisesRegex(
            TypeError,
            ("results must be a dictionary"),
        ):
            announce_failures(
                audio,
                [],  # type: ignore[arg-type]
            )

    def test_rejects_non_string_result_name(
        self,
    ) -> None:
        audio = make_audio()

        with self.assertRaisesRegex(
            TypeError,
            ("results must map strings to booleans"),
        ):
            announce_failures(
                audio,
                {
                    1: True,  # type: ignore[dict-item]
                },
            )

    def test_rejects_non_boolean_result(
        self,
    ) -> None:
        audio = make_audio()

        with self.assertRaisesRegex(
            TypeError,
            ("results must map strings to booleans"),
        ):
            announce_failures(
                audio,
                {
                    "hardware:i2c": 1,  # type: ignore[dict-item]
                },
            )


class CloseAudioTests(unittest.TestCase):
    def test_closes_audio(
        self,
    ) -> None:
        audio = make_audio()

        with patch.object(
            Audio,
            "close",
            return_value=None,
        ) as close:
            result = close_audio(audio)

        self.assertTrue(result)
        close.assert_called_once_with()

    def test_audio_error_is_logged(
        self,
    ) -> None:
        audio = make_audio()
        error = AudioError("cleanup failed")

        with (
            patch.object(
                Audio,
                "close",
                side_effect=error,
            ),
            patch(f"{MODULE}.log") as log_message,
        ):
            result = close_audio(audio)

        self.assertFalse(result)
        log_message.assert_called_once_with(
            "Audio cleanup failed: cleanup failed",
            DEFAULT_PLATFORM_CONFIG,
        )

    def test_cleanup_log_error_is_suppressed(
        self,
    ) -> None:
        audio = make_audio()

        with (
            patch.object(
                Audio,
                "close",
                side_effect=AudioError("cleanup failed"),
            ),
            patch(
                f"{MODULE}.log",
                side_effect=OSError("log unavailable"),
            ),
        ):
            result = close_audio(audio)

        self.assertFalse(result)

    def test_rejects_invalid_audio_before_close(
        self,
    ) -> None:
        with (
            patch.object(Audio, "close") as close,
            self.assertRaisesRegex(
                TypeError,
                "audio must be an Audio",
            ),
        ):
            close_audio(
                object()  # type: ignore[arg-type]
            )

        close.assert_not_called()

    def test_unexpected_close_error_propagates(
        self,
    ) -> None:
        audio = make_audio()
        error = RuntimeError("programming error")

        with (
            patch.object(
                Audio,
                "close",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            close_audio(audio)

        self.assertIs(
            context.exception,
            error,
        )


class MainTests(unittest.TestCase):
    def test_ready_boot_sequence(
        self,
    ) -> None:
        audio = make_audio()
        results = {
            "hardware:i2c": True,
        }

        with (
            patch(f"{MODULE}.log") as log_message,
            patch.object(
                Audio,
                "default",
                return_value=audio,
            ) as audio_default,
            patch(
                f"{MODULE}.say",
                return_value=True,
            ) as say_message,
            patch(
                f"{MODULE}.summarize_checks",
                return_value=(
                    True,
                    results,
                ),
            ) as summarize,
            patch(f"{MODULE}.announce_failures") as announce,
            patch(
                f"{MODULE}.close_audio",
                return_value=True,
            ) as close,
        ):
            result = main()

        self.assertEqual(result, 0)
        audio_default.assert_called_once_with(
            __import__(
                "betabox_robotics.robots",
                fromlist=["BETABOX_CAR"],
            ).BETABOX_CAR.audio
        )
        self.assertEqual(
            say_message.call_args_list,
            [
                call(
                    audio,
                    "Betabox starting",
                    DEFAULT_PLATFORM_CONFIG,
                ),
                call(
                    audio,
                    "Ready for class",
                    DEFAULT_PLATFORM_CONFIG,
                ),
            ],
        )
        summarize.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        announce.assert_not_called()
        self.assertEqual(
            log_message.call_args_list,
            [
                call(
                    "Boot announcer started",
                    DEFAULT_PLATFORM_CONFIG,
                ),
                call(
                    "Boot announce complete: ready",
                    DEFAULT_PLATFORM_CONFIG,
                ),
            ],
        )
        close.assert_called_once_with(
            audio,
            DEFAULT_PLATFORM_CONFIG,
        )

    def test_not_ready_boot_sequence(
        self,
    ) -> None:
        audio = make_audio()
        results = {
            "hardware:i2c": False,
        }

        with (
            patch(f"{MODULE}.log") as log_message,
            patch.object(
                Audio,
                "default",
                return_value=audio,
            ),
            patch(
                f"{MODULE}.say",
                return_value=True,
            ) as say_message,
            patch(
                f"{MODULE}.summarize_checks",
                return_value=(
                    False,
                    results,
                ),
            ),
            patch(f"{MODULE}.announce_failures") as announce,
            patch(
                f"{MODULE}.close_audio",
                return_value=True,
            ),
        ):
            result = main()

        self.assertEqual(result, 1)
        announce.assert_called_once_with(
            audio,
            results,
            DEFAULT_PLATFORM_CONFIG,
        )
        self.assertEqual(
            say_message.call_args_list,
            [
                call(
                    audio,
                    "Betabox starting",
                    DEFAULT_PLATFORM_CONFIG,
                ),
                call(
                    audio,
                    "Teacher help needed",
                    DEFAULT_PLATFORM_CONFIG,
                ),
            ],
        )
        self.assertEqual(
            log_message.call_args_list[-1],
            call(
                ("Boot announce complete: not ready"),
                DEFAULT_PLATFORM_CONFIG,
            ),
        )

    def test_startup_log_failure_returns_one(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.log",
                side_effect=OSError("log unavailable"),
            ),
            patch.object(Audio, "default") as audio_default,
        ):
            result = main()

        self.assertEqual(result, 1)
        audio_default.assert_not_called()

    def test_audio_initialization_failure_is_logged(
        self,
    ) -> None:
        error = AudioError("audio unavailable")

        with (
            patch(f"{MODULE}.log") as log_message,
            patch.object(
                Audio,
                "default",
                side_effect=error,
            ),
        ):
            result = main()

        self.assertEqual(result, 1)
        self.assertEqual(
            log_message.call_args_list,
            [
                call(
                    "Boot announcer started",
                    DEFAULT_PLATFORM_CONFIG,
                ),
                call(
                    ("Audio initialization failed: audio unavailable"),
                    DEFAULT_PLATFORM_CONFIG,
                ),
            ],
        )

    def test_audio_initialization_log_failure_is_suppressed(
        self,
    ) -> None:
        log_calls = 0

        def log_side_effect(
            message: str,
            config: object,
        ) -> None:
            nonlocal log_calls
            log_calls += 1

            if log_calls == 2:
                raise OSError("log unavailable")

        with (
            patch(
                f"{MODULE}.log",
                side_effect=log_side_effect,
            ),
            patch.object(
                Audio,
                "default",
                side_effect=AudioError("audio unavailable"),
            ),
        ):
            result = main()

        self.assertEqual(result, 1)

    def test_operational_error_is_logged_and_returns_one(
        self,
    ) -> None:
        audio = make_audio()

        with (
            patch(f"{MODULE}.log") as log_message,
            patch.object(
                Audio,
                "default",
                return_value=audio,
            ),
            patch(
                f"{MODULE}.say",
                return_value=True,
            ),
            patch(
                f"{MODULE}.summarize_checks",
                side_effect=RuntimeError("verification failed"),
            ),
            patch(
                f"{MODULE}.close_audio",
                return_value=True,
            ),
        ):
            result = main()

        self.assertEqual(result, 1)
        self.assertEqual(
            log_message.call_args_list[-1],
            call(
                ("Boot announce failed: verification failed"),
                DEFAULT_PLATFORM_CONFIG,
            ),
        )

    def test_operational_error_log_failure_is_suppressed(
        self,
    ) -> None:
        audio = make_audio()
        log_calls = 0

        def log_side_effect(
            message: str,
            config: object,
        ) -> None:
            nonlocal log_calls
            log_calls += 1

            if message.startswith("Boot announce failed:"):
                raise OSError("log unavailable")

        with (
            patch(
                f"{MODULE}.log",
                side_effect=log_side_effect,
            ),
            patch.object(
                Audio,
                "default",
                return_value=audio,
            ),
            patch(
                f"{MODULE}.say",
                return_value=True,
            ),
            patch(
                f"{MODULE}.summarize_checks",
                side_effect=RuntimeError("verification failed"),
            ),
            patch(
                f"{MODULE}.close_audio",
                return_value=True,
            ),
        ):
            result = main()

        self.assertEqual(result, 1)

    def test_cleanup_failure_changes_success_to_failure(
        self,
    ) -> None:
        audio = make_audio()

        with (
            patch(f"{MODULE}.log"),
            patch.object(
                Audio,
                "default",
                return_value=audio,
            ),
            patch(
                f"{MODULE}.say",
                return_value=True,
            ),
            patch(
                f"{MODULE}.summarize_checks",
                return_value=(
                    True,
                    {
                        "hardware:i2c": True,
                    },
                ),
            ),
            patch(
                f"{MODULE}.close_audio",
                return_value=False,
            ),
        ):
            result = main()

        self.assertEqual(result, 1)

    def test_unexpected_error_propagates_after_cleanup(
        self,
    ) -> None:
        audio = make_audio()
        error = AssertionError("programming error")

        with (
            patch(f"{MODULE}.log"),
            patch.object(
                Audio,
                "default",
                return_value=audio,
            ),
            patch(
                f"{MODULE}.say",
                side_effect=error,
            ),
            patch(
                f"{MODULE}.close_audio",
                return_value=True,
            ) as close,
            self.assertRaises(AssertionError) as context,
        ):
            main()

        self.assertIs(
            context.exception,
            error,
        )
        close.assert_called_once_with(
            audio,
            DEFAULT_PLATFORM_CONFIG,
        )


if __name__ == "__main__":
    unittest.main()
