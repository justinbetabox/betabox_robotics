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


class PicoSpeech(SpeechBackend):
    """pico2wave speech backend."""

    name: ClassVar[str] = "pico"
    executable_name: ClassVar[str] = "pico2wave"

    language: str

    def __init__(
        self,
        *,
        language: str = "en-US",
    ) -> None:
        language = language.strip()

        if not language:
            raise ValueError("language cannot be empty")

        self.language = language

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
            raise SpeechError("pico2wave executable not found")

        run_speech_command(
            [
                executable,
                "-l",
                self.language,
                "-w",
                str(path),
                speech_text,
            ],
            backend_name="pico2wave",
        )

        verify_speech_output(
            path,
            backend_name="pico2wave",
        )
