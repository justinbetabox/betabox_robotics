import shutil
import subprocess
import sys
from pathlib import Path

from betabox_robotics.audio.exceptions import AudioError
from betabox_robotics.audio.quiet import suppress_stderr
from betabox_robotics.audio.speech.base import SpeechBackend


class PiperSpeech(SpeechBackend):
    """Piper speech backend."""

    def __init__(self, model_path: str | Path, *, voice: str | None = None) -> None:
        self.model_path = Path(model_path).expanduser()
        self.voice = voice or self.model_path.stem
        self.name = "piper"

    @classmethod
    def executable(cls) -> str | None:
        venv_piper = Path(sys.executable).parent / "piper"

        if venv_piper.exists():
            return str(venv_piper)

        return shutil.which("piper")

    @classmethod
    def available(cls) -> bool:
        return cls.executable() is not None

    def synthesize(self, text: str, output_path: str | Path) -> None:
        executable = self.executable()

        if executable is None:
            raise AudioError("piper executable not found")

        command = [
            executable,
            "--model",
            str(self.model_path),
            "--output_file",
            str(output_path),
        ]

        try:
            with suppress_stderr():
                subprocess.run(
                    command,
                    input=text,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                )
        except subprocess.CalledProcessError as exc:
            raise AudioError(f"piper speech failed: {exc.stderr}") from exc
