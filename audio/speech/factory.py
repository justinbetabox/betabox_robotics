import os
from pathlib import Path

from betabox_car.audio.exceptions import AudioError
from betabox_car.audio.speech.base import SpeechBackend
from betabox_car.audio.speech.espeak_ng import EspeakNgSpeech
from betabox_car.audio.speech.pico import PicoSpeech
from betabox_car.audio.speech.piper import PiperSpeech


def create_backend(
    *,
    speech_engine: str = "auto",
    speech_language: str = "en-US",
    piper_model: str | Path | None = None,
    piper_voice: str = "en_US-amy-low",
) -> SpeechBackend:
    engine = speech_engine.lower()

    model_from_env = os.getenv("BETABOX_PIPER_MODEL")
    model = Path(piper_model).expanduser() if piper_model else None

    if model is None and model_from_env:
        model = Path(model_from_env).expanduser()

    if model is None:
        models_dir = Path(__file__).resolve().parents[1] / "models" / "piper"
        model = models_dir / f"{piper_voice}.onnx"

    if engine in ("auto", "pico", "pico2wave") and PicoSpeech.available():
        return PicoSpeech(language=speech_language)

    if engine in ("auto", "espeak-ng", "espeak_ng") and EspeakNgSpeech.available():
        return EspeakNgSpeech()

    if engine == "piper":
        model_from_env = os.getenv("BETABOX_PIPER_MODEL")
        model = Path(piper_model).expanduser() if piper_model else None

        if model is None and model_from_env:
            model = Path(model_from_env).expanduser()

        if model is None:
            models_dir = Path(__file__).resolve().parents[1] / "models" / "piper"
            model = models_dir / f"{piper_voice}.onnx"

        if model.exists() and PiperSpeech.available():
            return PiperSpeech(model_path=model, voice=piper_voice)

        raise AudioError(
            f"Piper requested, but piper or model path is not available: {model}"
        )

    raise AudioError("no supported speech backend found")


def available_backends() -> list[str]:
    backends: list[str] = []

    if PicoSpeech.available():
        backends.append("pico2wave")

    if EspeakNgSpeech.available():
        backends.append("espeak-ng")

    if PiperSpeech.available():
        backends.append("piper")

    return backends
