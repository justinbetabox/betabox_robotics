from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from betabox_robotics.audio.exceptions import SpeechError
from betabox_robotics.audio.speech.base import SpeechBackend
from betabox_robotics.audio.speech.espeak_ng import EspeakNgSpeech
from betabox_robotics.audio.speech.pico import PicoSpeech
from betabox_robotics.audio.speech.piper import PiperSpeech

DEFAULT_SPEECH_ENGINE: Final[str] = "auto"
DEFAULT_SPEECH_LANGUAGE: Final[str] = "en-US"
DEFAULT_PIPER_VOICE: Final[str] = "en_US-amy-low"

_ENGINE_ALIASES: Final[dict[str, str]] = {
    "auto": "auto",
    "pico": "pico",
    "pico2wave": "pico",
    "espeak": "espeak-ng",
    "espeak-ng": "espeak-ng",
    "espeak_ng": "espeak-ng",
    "piper": "piper",
}


def _require_nonempty_string(
    value: object,
    *,
    name: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{name} cannot be empty")

    return normalized


def _normalize_engine(
    speech_engine: object,
) -> str:
    requested = _require_nonempty_string(
        speech_engine,
        name="speech_engine",
    ).lower()

    engine = _ENGINE_ALIASES.get(requested)

    if engine is None:
        raise SpeechError(f"unknown speech engine: {speech_engine}")

    return engine


def _resolve_piper_model(
    *,
    piper_model: object,
    piper_voice: str,
) -> Path:
    if isinstance(piper_model, bool) or (
        piper_model is not None
        and not isinstance(
            piper_model,
            str | Path,
        )
    ):
        raise TypeError("piper_model must be a string, Path, or None")

    if piper_model is not None:
        return Path(piper_model).expanduser()

    model_from_env = os.getenv("BETABOX_PIPER_MODEL")

    if model_from_env:
        return Path(model_from_env).expanduser()

    models_dir = Path(__file__).resolve().parents[1] / "models" / "piper"

    return models_dir / f"{piper_voice}.onnx"


def _create_pico(
    *,
    language: str,
) -> SpeechBackend:
    if not PicoSpeech.available():
        raise SpeechError("pico2wave speech backend is not available")

    return PicoSpeech(language=language)


def _create_espeak(
    *,
    language: str,
) -> SpeechBackend:
    if not EspeakNgSpeech.available():
        raise SpeechError("espeak-ng speech backend is not available")

    return EspeakNgSpeech(voice=language.lower())


def _create_piper(
    *,
    model_path: Path,
    voice: str,
) -> SpeechBackend:
    if not PiperSpeech.available():
        raise SpeechError("piper speech backend is not available")

    if not model_path.is_file():
        raise SpeechError(f"Piper model not found: {model_path}")

    return PiperSpeech(
        model_path=model_path,
        voice=voice,
    )


def create_backend(
    *,
    speech_engine: str = DEFAULT_SPEECH_ENGINE,
    speech_language: str = DEFAULT_SPEECH_LANGUAGE,
    piper_model: str | Path | None = None,
    piper_voice: str = DEFAULT_PIPER_VOICE,
) -> SpeechBackend:
    engine = _normalize_engine(speech_engine)

    language = _require_nonempty_string(
        speech_language,
        name="speech_language",
    )

    voice = _require_nonempty_string(
        piper_voice,
        name="piper_voice",
    )

    if engine == "pico":
        return _create_pico(language=language)

    if engine == "espeak-ng":
        return _create_espeak(language=language)

    if engine == "piper":
        model_path = _resolve_piper_model(
            piper_model=piper_model,
            piper_voice=voice,
        )

        return _create_piper(
            model_path=model_path,
            voice=voice,
        )

    # Auto intentionally prefers lightweight system backends.
    if PicoSpeech.available():
        return PicoSpeech(language=language)

    if EspeakNgSpeech.available():
        return EspeakNgSpeech(voice=language.lower())

    raise SpeechError("no supported speech backend found")


def available_backends() -> list[str]:
    backends: list[str] = []

    if PicoSpeech.available():
        backends.append("pico2wave")

    if EspeakNgSpeech.available():
        backends.append("espeak-ng")

    if PiperSpeech.available():
        backends.append("piper")

    return backends
