from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from betabox_robotics.audio import SpeechError
from betabox_robotics.audio.speech.piper import (
    PiperSpeech,
)


class PiperConstructionTests(unittest.TestCase):
    def test_stores_model_and_default_voice(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "amy.onnx"
            model.touch()

            backend = PiperSpeech(
                model,
            )

            self.assertEqual(
                backend.model_path,
                model,
            )
            self.assertEqual(
                backend.voice,
                "amy",
            )
            self.assertEqual(
                backend.name,
                "piper",
            )

    def test_stores_explicit_voice(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "amy.onnx"
            model.touch()

            backend = PiperSpeech(
                model,
                voice="custom-voice",
            )

            self.assertEqual(
                backend.voice,
                "custom-voice",
            )

    def test_rejects_invalid_model_path_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "model_path must be a string or Path",
        ):
            PiperSpeech(
                True,  # type: ignore[arg-type]
            )

    def test_rejects_missing_model(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            SpeechError,
            "Piper model not found",
        ):
            PiperSpeech(
                "/missing/model.onnx",
            )

    def test_rejects_non_string_voice(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "amy.onnx"
            model.touch()

            with self.assertRaisesRegex(
                TypeError,
                "voice must be a string or None",
            ):
                PiperSpeech(
                    model,
                    voice=123,  # type: ignore[arg-type]
                )

    def test_rejects_empty_voice(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "amy.onnx"
            model.touch()

            with self.assertRaisesRegex(
                ValueError,
                "voice cannot be empty",
            ):
                PiperSpeech(
                    model,
                    voice=" ",
                )


class PiperExecutableTests(unittest.TestCase):
    def test_prefers_venv_executable(
        self,
    ) -> None:
        fake_python = Path("/opt/betabox/venv/bin/python")
        expected = fake_python.parent / "piper"

        with (
            patch(
                "betabox_robotics.audio.speech.piper.sys.executable",
                str(fake_python),
            ),
            patch.object(
                Path,
                "is_file",
                return_value=True,
            ),
            patch(
                "betabox_robotics.audio.speech.piper.os.access",
                return_value=True,
            ),
            patch(
                "betabox_robotics.audio.speech.piper.shutil.which",
            ) as which,
        ):
            result = PiperSpeech.executable()

        self.assertEqual(
            result,
            str(expected),
        )
        which.assert_not_called()

    def test_falls_back_to_path_executable(
        self,
    ) -> None:
        with (
            patch.object(
                Path,
                "is_file",
                return_value=False,
            ),
            patch(
                "betabox_robotics.audio.speech.piper.shutil.which",
                return_value="/usr/local/bin/piper",
            ),
        ):
            self.assertEqual(
                PiperSpeech.executable(),
                "/usr/local/bin/piper",
            )

    def test_ignores_non_executable_venv_file(
        self,
    ) -> None:
        with (
            patch.object(
                Path,
                "is_file",
                return_value=True,
            ),
            patch(
                "betabox_robotics.audio.speech.piper.os.access",
                return_value=False,
            ),
            patch(
                "betabox_robotics.audio.speech.piper.shutil.which",
                return_value=None,
            ),
        ):
            self.assertIsNone(PiperSpeech.executable())


class PiperSynthesisTests(unittest.TestCase):
    def test_synthesize_builds_expected_command(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "amy.onnx"
            model.touch()

            backend = PiperSpeech(
                model,
                voice="amy",
            )

            output = Path(directory) / "speech.wav"
            quiet_context = MagicMock()
            quiet_context.__enter__.return_value = None
            quiet_context.__exit__.return_value = None

            with (
                patch.object(
                    backend,
                    "executable",
                    return_value="/usr/bin/piper",
                ),
                patch(
                    "betabox_robotics.audio.speech.piper.validate_speech_request",
                    return_value=(
                        "Hello",
                        output,
                    ),
                ),
                patch(
                    "betabox_robotics.audio.speech.piper.suppress_stderr",
                    return_value=quiet_context,
                ) as suppress,
                patch(
                    "betabox_robotics.audio.speech.piper.run_speech_command",
                ) as run,
                patch(
                    "betabox_robotics.audio.speech.piper.verify_speech_output",
                ) as verify,
            ):
                backend.synthesize(
                    "Hello",
                    output,
                )

            suppress.assert_called_once_with()

            run.assert_called_once_with(
                [
                    "/usr/bin/piper",
                    "--model",
                    str(model),
                    "--output_file",
                    str(output),
                ],
                backend_name="piper",
                input_text="Hello",
            )

            verify.assert_called_once_with(
                output,
                backend_name="piper",
            )

    def test_rejects_missing_executable(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "amy.onnx"
            model.touch()

            backend = PiperSpeech(
                model,
            )

            with (
                patch.object(
                    backend,
                    "executable",
                    return_value=None,
                ),
                self.assertRaisesRegex(
                    SpeechError,
                    "piper executable not found",
                ),
            ):
                backend.synthesize(
                    "Hello",
                    Path(directory) / "speech.wav",
                )


if __name__ == "__main__":
    unittest.main()
