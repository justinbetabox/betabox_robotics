from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from betabox_robotics.audio import SpeechError
from betabox_robotics.audio.speech.utils import (
    SPEECH_TIMEOUT_SECONDS,
    run_speech_command,
    validate_speech_request,
    verify_speech_output,
)


class ValidateSpeechRequestTests(unittest.TestCase):
    def test_accepts_text_and_string_path(
        self,
    ) -> None:
        text, path = validate_speech_request(
            "Hello",
            "/tmp/speech.wav",
        )

        self.assertEqual(
            text,
            "Hello",
        )
        self.assertEqual(
            path,
            Path("/tmp/speech.wav"),
        )

    def test_accepts_path_object(
        self,
    ) -> None:
        requested = Path("~/speech.wav")

        _, path = validate_speech_request(
            "Hello",
            requested,
        )

        self.assertEqual(
            path,
            requested.expanduser(),
        )

    def test_preserves_text_whitespace(
        self,
    ) -> None:
        text, _ = validate_speech_request(
            "  Hello world  ",
            "/tmp/speech.wav",
        )

        self.assertEqual(
            text,
            "  Hello world  ",
        )

    def test_rejects_non_string_text(
        self,
    ) -> None:
        for text in (
            None,
            123,
            True,
            object(),
        ):
            with (
                self.subTest(text=text),
                self.assertRaisesRegex(
                    TypeError,
                    "text must be a string",
                ),
            ):
                validate_speech_request(
                    text,  # type: ignore[arg-type]
                    "/tmp/speech.wav",
                )

    def test_rejects_empty_text(
        self,
    ) -> None:
        for text in (
            "",
            " ",
            "\n",
            "\t",
        ):
            with (
                self.subTest(text=text),
                self.assertRaisesRegex(
                    ValueError,
                    "text cannot be empty",
                ),
            ):
                validate_speech_request(
                    text,
                    "/tmp/speech.wav",
                )

    def test_rejects_invalid_output_path_type(
        self,
    ) -> None:
        for output_path in (
            None,
            True,
            123,
            object(),
        ):
            with (
                self.subTest(output_path=output_path),
                self.assertRaisesRegex(
                    TypeError,
                    "output_path must be a string or Path",
                ),
            ):
                validate_speech_request(
                    "Hello",
                    output_path,  # type: ignore[arg-type]
                )

    def test_rejects_output_directory(
        self,
    ) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(
                ValueError,
                "output_path must not be a directory",
            ),
        ):
            validate_speech_request(
                "Hello",
                directory,
            )

    def test_rejects_non_wav_extension(
        self,
    ) -> None:
        for path in (
            "/tmp/speech.mp3",
            "/tmp/speech",
            "/tmp/speech.txt",
        ):
            with (
                self.subTest(path=path),
                self.assertRaisesRegex(
                    ValueError,
                    r"output_path must use the \.wav extension",
                ),
            ):
                validate_speech_request(
                    "Hello",
                    path,
                )

    def test_wav_extension_is_case_insensitive(
        self,
    ) -> None:
        _, path = validate_speech_request(
            "Hello",
            "/tmp/speech.WAV",
        )

        self.assertEqual(
            path.suffix,
            ".WAV",
        )


class RunSpeechCommandTests(unittest.TestCase):
    def test_runs_command_with_expected_arguments(
        self,
    ) -> None:
        completed = subprocess.CompletedProcess(
            args=["speech"],
            returncode=0,
        )

        with patch(
            "betabox_robotics.audio.speech.utils.subprocess.run",
            return_value=completed,
        ) as run:
            run_speech_command(
                [
                    "speech",
                    "--output",
                    "test.wav",
                ],
                backend_name="test",
                input_text="Hello",
                timeout=4.0,
            )

        run.assert_called_once_with(
            [
                "speech",
                "--output",
                "test.wav",
            ],
            input="Hello",
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=4.0,
        )

    def test_uses_default_timeout(
        self,
    ) -> None:
        completed = subprocess.CompletedProcess(
            args=["speech"],
            returncode=0,
        )

        with patch(
            "betabox_robotics.audio.speech.utils.subprocess.run",
            return_value=completed,
        ) as run:
            run_speech_command(
                ["speech"],
                backend_name="test",
            )

        self.assertEqual(
            run.call_args.kwargs["timeout"],
            SPEECH_TIMEOUT_SECONDS,
        )

    def test_wraps_timeout(
        self,
    ) -> None:
        error = subprocess.TimeoutExpired(
            cmd=["speech"],
            timeout=3,
        )

        with (
            patch(
                "betabox_robotics.audio.speech.utils.subprocess.run",
                side_effect=error,
            ),
            self.assertRaisesRegex(
                SpeechError,
                "test speech timed out after 3 seconds",
            ) as raised,
        ):
            run_speech_command(
                ["speech"],
                backend_name="test",
                timeout=3,
            )

        self.assertIs(
            raised.exception.__cause__,
            error,
        )

    def test_wraps_os_error(
        self,
    ) -> None:
        error = OSError("executable missing")

        with (
            patch(
                "betabox_robotics.audio.speech.utils.subprocess.run",
                side_effect=error,
            ),
            self.assertRaisesRegex(
                SpeechError,
                "failed to start test",
            ) as raised,
        ):
            run_speech_command(
                ["speech"],
                backend_name="test",
            )

        self.assertIs(
            raised.exception.__cause__,
            error,
        )

    def test_wraps_called_process_error_with_stderr(
        self,
    ) -> None:
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["speech"],
            stderr="backend failed\n",
        )

        with (
            patch(
                "betabox_robotics.audio.speech.utils.subprocess.run",
                side_effect=error,
            ),
            self.assertRaisesRegex(
                SpeechError,
                "test speech failed: backend failed",
            ) as raised,
        ):
            run_speech_command(
                ["speech"],
                backend_name="test",
            )

        self.assertIs(
            raised.exception.__cause__,
            error,
        )

    def test_wraps_called_process_error_without_stderr(
        self,
    ) -> None:
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["speech"],
            stderr=None,
        )

        with (
            patch(
                "betabox_robotics.audio.speech.utils.subprocess.run",
                side_effect=error,
            ),
            self.assertRaisesRegex(
                SpeechError,
                "^test speech failed$",
            ),
        ):
            run_speech_command(
                ["speech"],
                backend_name="test",
            )


class VerifySpeechOutputTests(unittest.TestCase):
    def test_accepts_nonempty_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "speech.wav"
            path.write_bytes(b"RIFFdata")

            verify_speech_output(
                path,
                backend_name="test",
            )

    def test_rejects_missing_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.wav"

            with self.assertRaisesRegex(
                SpeechError,
                "test did not create a valid WAV file",
            ):
                verify_speech_output(
                    path,
                    backend_name="test",
                )

    def test_rejects_empty_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.wav"
            path.touch()

            with self.assertRaisesRegex(
                SpeechError,
                "test did not create a valid WAV file",
            ):
                verify_speech_output(
                    path,
                    backend_name="test",
                )

    def test_rejects_directory(
        self,
    ) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(
                SpeechError,
                "test did not create a valid WAV file",
            ),
        ):
            verify_speech_output(
                Path(directory),
                backend_name="test",
            )

    def test_wraps_stat_error(
        self,
    ) -> None:
        path = Path("/tmp/speech.wav")
        error = OSError("stat failed")

        with (
            patch.object(
                Path,
                "is_file",
                side_effect=error,
            ),
            self.assertRaisesRegex(
                SpeechError,
                "failed to inspect test output",
            ) as raised,
        ):
            verify_speech_output(
                path,
                backend_name="test",
            )

        self.assertIs(
            raised.exception.__cause__,
            error,
        )


if __name__ == "__main__":
    unittest.main()
