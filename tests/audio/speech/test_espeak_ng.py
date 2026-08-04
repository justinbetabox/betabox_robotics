from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from betabox_robotics.audio import SpeechError
from betabox_robotics.audio.speech.espeak_ng import (
    EspeakNgSpeech,
)


class EspeakNgConstructionTests(unittest.TestCase):
    def test_stores_voice(
        self,
    ) -> None:
        backend = EspeakNgSpeech(
            voice="en-gb",
        )

        self.assertEqual(
            backend.voice,
            "en-gb",
        )
        self.assertEqual(
            backend.name,
            "espeak-ng",
        )

    def test_strips_voice(
        self,
    ) -> None:
        backend = EspeakNgSpeech(
            voice="  en-us  ",
        )

        self.assertEqual(
            backend.voice,
            "en-us",
        )

    def test_rejects_non_string_voice(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "voice must be a string",
        ):
            EspeakNgSpeech(
                voice=123,  # type: ignore[arg-type]
            )

    def test_rejects_empty_voice(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "voice cannot be empty",
        ):
            EspeakNgSpeech(
                voice=" ",
            )


class EspeakNgAvailabilityTests(unittest.TestCase):
    def test_executable_returns_discovered_path(
        self,
    ) -> None:
        with patch(
            "betabox_robotics.audio.speech.espeak_ng.shutil.which",
            return_value="/usr/bin/espeak-ng",
        ):
            self.assertEqual(
                EspeakNgSpeech.executable(),
                "/usr/bin/espeak-ng",
            )

    def test_available_is_true_when_executable_exists(
        self,
    ) -> None:
        with patch.object(
            EspeakNgSpeech,
            "executable",
            return_value="/usr/bin/espeak-ng",
        ):
            self.assertTrue(EspeakNgSpeech.available())

    def test_available_is_false_when_executable_is_missing(
        self,
    ) -> None:
        with patch.object(
            EspeakNgSpeech,
            "executable",
            return_value=None,
        ):
            self.assertFalse(EspeakNgSpeech.available())


class EspeakNgSynthesisTests(unittest.TestCase):
    def test_synthesize_builds_expected_command(
        self,
    ) -> None:
        backend = EspeakNgSpeech(
            voice="en-us",
        )
        path = Path("/tmp/speech.wav")

        with (
            patch.object(
                backend,
                "executable",
                return_value="/usr/bin/espeak-ng",
            ),
            patch(
                "betabox_robotics.audio.speech.espeak_ng.validate_speech_request",
                return_value=(
                    "Hello",
                    path,
                ),
            ) as validate,
            patch(
                "betabox_robotics.audio.speech.espeak_ng.run_speech_command",
            ) as run,
            patch(
                "betabox_robotics.audio.speech.espeak_ng.verify_speech_output",
            ) as verify,
        ):
            backend.synthesize(
                "Hello",
                path,
            )

        validate.assert_called_once_with(
            "Hello",
            path,
        )

        run.assert_called_once_with(
            [
                "/usr/bin/espeak-ng",
                "-v",
                "en-us",
                "-w",
                str(path),
                "Hello",
            ],
            backend_name="espeak-ng",
        )

        verify.assert_called_once_with(
            path,
            backend_name="espeak-ng",
        )

    def test_synthesize_rejects_missing_executable(
        self,
    ) -> None:
        backend = EspeakNgSpeech()

        with (
            patch.object(
                backend,
                "executable",
                return_value=None,
            ),
            self.assertRaisesRegex(
                SpeechError,
                "espeak-ng executable not found",
            ),
        ):
            backend.synthesize(
                "Hello",
                "/tmp/speech.wav",
            )

    def test_does_not_verify_when_command_fails(
        self,
    ) -> None:
        backend = EspeakNgSpeech()

        with (
            patch.object(
                backend,
                "executable",
                return_value="/usr/bin/espeak-ng",
            ),
            patch(
                "betabox_robotics.audio.speech.espeak_ng.run_speech_command",
                side_effect=SpeechError("speech failed"),
            ),
            patch(
                "betabox_robotics.audio.speech.espeak_ng.verify_speech_output",
            ) as verify,
            self.assertRaises(SpeechError),
        ):
            backend.synthesize(
                "Hello",
                "/tmp/speech.wav",
            )

        verify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
