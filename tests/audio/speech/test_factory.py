from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from betabox_robotics.audio import SpeechError
from betabox_robotics.audio.speech.espeak_ng import (
    EspeakNgSpeech,
)
from betabox_robotics.audio.speech.factory import (
    _normalize_engine,
    _require_nonempty_string,
    _resolve_piper_model,
    available_backends,
    create_backend,
)
from betabox_robotics.audio.speech.pico import PicoSpeech
from betabox_robotics.audio.speech.piper import PiperSpeech


class FactoryValidationTests(unittest.TestCase):
    def test_require_nonempty_string_strips_value(
        self,
    ) -> None:
        self.assertEqual(
            _require_nonempty_string(
                "  hello  ",
                name="value",
            ),
            "hello",
        )

    def test_require_nonempty_string_rejects_non_string(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "value must be a string",
        ):
            _require_nonempty_string(
                123,
                name="value",
            )

    def test_require_nonempty_string_rejects_empty_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "value cannot be empty",
        ):
            _require_nonempty_string(
                " ",
                name="value",
            )

    def test_normalizes_engine_aliases(
        self,
    ) -> None:
        aliases = {
            "AUTO": "auto",
            "pico": "pico",
            "pico2wave": "pico",
            "espeak": "espeak-ng",
            "espeak-ng": "espeak-ng",
            "espeak_ng": "espeak-ng",
            "piper": "piper",
        }

        for requested, expected in aliases.items():
            with self.subTest(requested=requested):
                self.assertEqual(
                    _normalize_engine(requested),
                    expected,
                )

    def test_rejects_unknown_engine(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            SpeechError,
            "unknown speech engine",
        ):
            _normalize_engine("unknown")


class PiperModelResolutionTests(unittest.TestCase):
    def test_explicit_model_has_priority(
        self,
    ) -> None:
        with patch.dict(
            os.environ,
            {
                "BETABOX_PIPER_MODEL": "/env/model.onnx",
            },
        ):
            result = _resolve_piper_model(
                piper_model="/explicit/model.onnx",
                piper_voice="amy",
            )

        self.assertEqual(
            result,
            Path("/explicit/model.onnx"),
        )

    def test_uses_environment_model(
        self,
    ) -> None:
        with patch.dict(
            os.environ,
            {
                "BETABOX_PIPER_MODEL": "/env/model.onnx",
            },
        ):
            result = _resolve_piper_model(
                piper_model=None,
                piper_voice="amy",
            )

        self.assertEqual(
            result,
            Path("/env/model.onnx"),
        )

    def test_uses_packaged_default_model(
        self,
    ) -> None:
        with patch.dict(
            os.environ,
            {},
            clear=True,
        ):
            result = _resolve_piper_model(
                piper_model=None,
                piper_voice="amy",
            )

        self.assertEqual(
            result.name,
            "amy.onnx",
        )
        self.assertEqual(
            result.parent.name,
            "piper",
        )

    def test_rejects_invalid_model_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "piper_model must be a string, Path, or None",
        ):
            _resolve_piper_model(
                piper_model=True,  # type: ignore[arg-type]
                piper_voice="amy",
            )


class CreateBackendTests(unittest.TestCase):
    def test_explicit_pico(
        self,
    ) -> None:
        with patch.object(
            PicoSpeech,
            "available",
            return_value=True,
        ):
            backend = create_backend(
                speech_engine="pico",
                speech_language="en-GB",
            )

        self.assertIsInstance(
            backend,
            PicoSpeech,
        )
        self.assertEqual(
            backend.language,
            "en-GB",
        )

    def test_explicit_pico_unavailable(
        self,
    ) -> None:
        with (
            patch.object(
                PicoSpeech,
                "available",
                return_value=False,
            ),
            self.assertRaisesRegex(
                SpeechError,
                "pico2wave speech backend is not available",
            ),
        ):
            create_backend(
                speech_engine="pico",
            )

    def test_explicit_espeak(
        self,
    ) -> None:
        with patch.object(
            EspeakNgSpeech,
            "available",
            return_value=True,
        ):
            backend = create_backend(
                speech_engine="espeak-ng",
                speech_language="EN-US",
            )

        self.assertIsInstance(
            backend,
            EspeakNgSpeech,
        )
        self.assertEqual(
            backend.voice,
            "en-us",
        )

    def test_auto_prefers_pico(
        self,
    ) -> None:
        with (
            patch.object(
                PicoSpeech,
                "available",
                return_value=True,
            ),
            patch.object(
                EspeakNgSpeech,
                "available",
                return_value=True,
            ),
        ):
            backend = create_backend()

        self.assertIsInstance(
            backend,
            PicoSpeech,
        )

    def test_auto_falls_back_to_espeak(
        self,
    ) -> None:
        with (
            patch.object(
                PicoSpeech,
                "available",
                return_value=False,
            ),
            patch.object(
                EspeakNgSpeech,
                "available",
                return_value=True,
            ),
        ):
            backend = create_backend()

        self.assertIsInstance(
            backend,
            EspeakNgSpeech,
        )

    def test_auto_raises_when_no_backend_available(
        self,
    ) -> None:
        with (
            patch.object(
                PicoSpeech,
                "available",
                return_value=False,
            ),
            patch.object(
                EspeakNgSpeech,
                "available",
                return_value=False,
            ),
            self.assertRaisesRegex(
                SpeechError,
                "no supported speech backend found",
            ),
        ):
            create_backend()

    def test_explicit_piper(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "amy.onnx"
            model.touch()

            with patch.object(
                PiperSpeech,
                "available",
                return_value=True,
            ):
                backend = create_backend(
                    speech_engine="piper",
                    piper_model=model,
                    piper_voice="amy",
                )

            self.assertIsInstance(
                backend,
                PiperSpeech,
            )
            self.assertEqual(
                backend.model_path,
                model,
            )
            self.assertEqual(
                backend.voice,
                "amy",
            )

    def test_piper_rejects_missing_model(
        self,
    ) -> None:
        with (
            patch.object(
                PiperSpeech,
                "available",
                return_value=True,
            ),
            self.assertRaisesRegex(
                SpeechError,
                "Piper model not found",
            ),
        ):
            create_backend(
                speech_engine="piper",
                piper_model="/missing/model.onnx",
            )

    def test_piper_rejects_missing_executable(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "amy.onnx"
            model.touch()

            with (
                patch.object(
                    PiperSpeech,
                    "available",
                    return_value=False,
                ),
                self.assertRaisesRegex(
                    SpeechError,
                    "piper speech backend is not available",
                ),
            ):
                create_backend(
                    speech_engine="piper",
                    piper_model=model,
                )

    def test_validates_language_before_selection(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "speech_language cannot be empty",
        ):
            create_backend(
                speech_language=" ",
            )

    def test_validates_piper_voice_before_selection(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "piper_voice cannot be empty",
        ):
            create_backend(
                piper_voice=" ",
            )


class AvailableBackendsTests(unittest.TestCase):
    def test_returns_available_backends_in_priority_order(
        self,
    ) -> None:
        with (
            patch.object(
                PicoSpeech,
                "available",
                return_value=True,
            ),
            patch.object(
                EspeakNgSpeech,
                "available",
                return_value=True,
            ),
            patch.object(
                PiperSpeech,
                "available",
                return_value=True,
            ),
        ):
            self.assertEqual(
                available_backends(),
                [
                    "pico2wave",
                    "espeak-ng",
                    "piper",
                ],
            )

    def test_omits_unavailable_backends(
        self,
    ) -> None:
        with (
            patch.object(
                PicoSpeech,
                "available",
                return_value=False,
            ),
            patch.object(
                EspeakNgSpeech,
                "available",
                return_value=True,
            ),
            patch.object(
                PiperSpeech,
                "available",
                return_value=False,
            ),
        ):
            self.assertEqual(
                available_backends(),
                [
                    "espeak-ng",
                ],
            )


if __name__ == "__main__":
    unittest.main()
