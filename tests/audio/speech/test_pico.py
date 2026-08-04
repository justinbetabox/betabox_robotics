from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from betabox_robotics.audio import SpeechError
from betabox_robotics.audio.speech.pico import (
    PicoSpeech,
)


class PicoConstructionTests(unittest.TestCase):
    def test_stores_language(
        self,
    ) -> None:
        backend = PicoSpeech(
            language="en-GB",
        )

        self.assertEqual(
            backend.language,
            "en-GB",
        )
        self.assertEqual(
            backend.name,
            "pico",
        )

    def test_strips_language(
        self,
    ) -> None:
        backend = PicoSpeech(
            language="  en-US  ",
        )

        self.assertEqual(
            backend.language,
            "en-US",
        )

    def test_rejects_non_string_language(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "language must be a string",
        ):
            PicoSpeech(
                language=123,  # type: ignore[arg-type]
            )

    def test_rejects_empty_language(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "language cannot be empty",
        ):
            PicoSpeech(
                language=" ",
            )


class PicoAvailabilityTests(unittest.TestCase):
    def test_executable_returns_discovered_path(
        self,
    ) -> None:
        with patch(
            "betabox_robotics.audio.speech.pico.shutil.which",
            return_value="/usr/bin/pico2wave",
        ):
            self.assertEqual(
                PicoSpeech.executable(),
                "/usr/bin/pico2wave",
            )

    def test_available_reflects_executable(
        self,
    ) -> None:
        with patch.object(
            PicoSpeech,
            "executable",
            return_value="/usr/bin/pico2wave",
        ):
            self.assertTrue(PicoSpeech.available())

        with patch.object(
            PicoSpeech,
            "executable",
            return_value=None,
        ):
            self.assertFalse(PicoSpeech.available())


class PicoSynthesisTests(unittest.TestCase):
    def test_synthesize_builds_expected_command(
        self,
    ) -> None:
        backend = PicoSpeech(
            language="en-US",
        )
        path = Path("/tmp/speech.wav")

        with (
            patch.object(
                backend,
                "executable",
                return_value="/usr/bin/pico2wave",
            ),
            patch(
                "betabox_robotics.audio.speech.pico.validate_speech_request",
                return_value=(
                    "Hello",
                    path,
                ),
            ),
            patch(
                "betabox_robotics.audio.speech.pico.run_speech_command",
            ) as run,
            patch(
                "betabox_robotics.audio.speech.pico.verify_speech_output",
            ) as verify,
        ):
            backend.synthesize(
                "Hello",
                path,
            )

        run.assert_called_once_with(
            [
                "/usr/bin/pico2wave",
                "-l",
                "en-US",
                "-w",
                str(path),
                "Hello",
            ],
            backend_name="pico2wave",
        )

        verify.assert_called_once_with(
            path,
            backend_name="pico2wave",
        )

    def test_rejects_missing_executable(
        self,
    ) -> None:
        backend = PicoSpeech()

        with (
            patch.object(
                backend,
                "executable",
                return_value=None,
            ),
            self.assertRaisesRegex(
                SpeechError,
                "pico2wave executable not found",
            ),
        ):
            backend.synthesize(
                "Hello",
                "/tmp/speech.wav",
            )


if __name__ == "__main__":
    unittest.main()
