import shutil
import subprocess
from pathlib import Path

from betabox_car.audio.exceptions import AudioError
from betabox_car.audio.speech.base import SpeechBackend


class EspeakNgSpeech(SpeechBackend):
    """espeak-ng speech backend."""

    name = "espeak-ng"

    def __init__(self, *, voice: str = "en-us") -> None:
        self.voice = voice
        self.name = "espeak-ng"

    @classmethod
    def available(cls) -> bool:
        return shutil.which("espeak-ng") is not None

    def synthesize(self, text: str, output_path: str | Path) -> None:
        command = [
            "espeak-ng",
            "-v",
            self.voice,
            "-w",
            str(output_path),
            text,
        ]

        try:
            subprocess.run(
                command,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            raise AudioError(f"espeak-ng speech failed: {exc.stderr}") from exc
