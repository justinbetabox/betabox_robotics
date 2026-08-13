from __future__ import annotations

import shutil
from typing import ClassVar

from typing_extensions import override

from betabox_robotics.audio.exceptions import SpeechError
from betabox_robotics.audio.speech.base import (
    SpeechBackend,
    SpeechOutputPath,
)
from betabox_robotics.audio.speech.utils import (
    run_speech_command,
    validate_speech_request,
    verify_speech_output,
)


class EspeakNgSpeech(SpeechBackend):
    """espeak-ng speech backend."""

    name: ClassVar[str] = "espeak-ng"
    executable_name: ClassVar[str] = "espeak-ng"

    voice: str

    def __init__(
        self,
        *,
        voice: str = "en-us",
    ) -> None:
        voice = voice.strip()

        if not voice:
            raise ValueError("voice cannot be empty")

        self.voice = voice.strip()

    @classmethod
    def executable(
        cls,
    ) -> str | None:
        return shutil.which(cls.executable_name)

    @classmethod
    def available(
        cls,
    ) -> bool:
        return cls.executable() is not None

    @override
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
            raise SpeechError("espeak-ng executable not found")

        run_speech_command(
            [
                executable,
                "-v",
                self.voice,
                "-w",
                str(path),
                speech_text,
            ],
            backend_name=self.name,
        )

        verify_speech_output(
            path,
            backend_name=self.name,
        )
