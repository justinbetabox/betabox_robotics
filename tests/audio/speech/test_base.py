from __future__ import annotations

import unittest
from pathlib import Path

from betabox_robotics.audio.speech.base import (
    SpeechBackend,
    SpeechOutputPath,
)


class FakeSpeechBackend(SpeechBackend):
    def synthesize(
        self,
        text: str,
        output_path: SpeechOutputPath,
    ) -> None:
        return None


class SpeechBackendTests(unittest.TestCase):
    def test_abstract_backend_cannot_be_instantiated(
        self,
    ) -> None:
        with self.assertRaises(TypeError):
            SpeechBackend()

    def test_concrete_backend_can_be_instantiated(
        self,
    ) -> None:
        backend = FakeSpeechBackend()

        self.assertIsInstance(
            backend,
            SpeechBackend,
        )

    def test_concrete_backend_accepts_string_path(
        self,
    ) -> None:
        backend = FakeSpeechBackend()

        self.assertIsNone(
            backend.synthesize(
                "Hello",
                "/tmp/test.wav",
            )
        )

    def test_concrete_backend_accepts_path_object(
        self,
    ) -> None:
        backend = FakeSpeechBackend()

        self.assertIsNone(
            backend.synthesize(
                "Hello",
                Path("/tmp/test.wav"),
            )
        )


if __name__ == "__main__":
    unittest.main()
