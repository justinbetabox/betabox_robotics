from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import ClassVar

from betabox_robotics.audio.exceptions import SpeechError
from betabox_robotics.audio.quiet import suppress_stderr
from betabox_robotics.audio.speech.base import (
    SpeechBackend,
    SpeechOutputPath,
)
from betabox_robotics.audio.speech.utils import (
    run_speech_command,
    validate_speech_request,
    verify_speech_output,
)


class PiperSpeech(SpeechBackend):
    """Piper speech backend."""

    name: ClassVar[str] = "piper"

    def __init__(
        self,
        model_path: str | Path,
        *,
        voice: str | None = None,
    ) -> None:
        if isinstance(model_path, bool) or not isinstance(
            model_path,
            str | Path,
        ):
            raise TypeError("model_path must be a string or Path")

        path = Path(model_path).expanduser()

        if not path.is_file():
            raise SpeechError(f"Piper model not found: {path}")

        if voice is not None:
            if not isinstance(voice, str):
                raise TypeError("voice must be a string or None")

            if not voice.strip():
                raise ValueError("voice cannot be empty")

        self.model_path = path
        self.voice = voice.strip() if voice is not None else path.stem

    @classmethod
    def executable(
        cls,
    ) -> str | None:
        venv_piper = Path(sys.executable).parent / "piper"

        if venv_piper.is_file() and os.access(
            venv_piper,
            os.X_OK,
        ):
            return str(venv_piper)

        return shutil.which("piper")

    @classmethod
    def available(
        cls,
    ) -> bool:
        return cls.executable() is not None

    def synthesize(
        self,
        text: str,
        output_path: SpeechOutputPath,
    ) -> None:
        speech_text, path = validate_speech_request(
            text,
            output_path,
        )

        executable = self.executable()

        if executable is None:
            raise SpeechError("piper executable not found")

        command = [
            executable,
            "--model",
            str(self.model_path),
            "--output_file",
            str(path),
        ]

        with suppress_stderr():
            run_speech_command(
                command,
                backend_name=self.name,
                input_text=speech_text,
            )

        verify_speech_output(
            path,
            backend_name=self.name,
        )
