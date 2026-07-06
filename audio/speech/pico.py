import shutil
import subprocess
from pathlib import Path

from betabox_robotics.audio.exceptions import AudioError
from betabox_robotics.audio.speech.base import SpeechBackend


class PicoSpeech(SpeechBackend):
    """pico2wave speech backend."""

    def __init__(self, *, language: str = "en-US") -> None:
        self.language = language
        self.name = "pico"

    @classmethod
    def available(cls) -> bool:
        return shutil.which("pico2wave") is not None

    def synthesize(self, text: str, output_path: str | Path) -> None:
        command = [
            "pico2wave",
            "-l",
            self.language,
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
            raise AudioError(f"pico2wave speech failed: {exc.stderr}") from exc
