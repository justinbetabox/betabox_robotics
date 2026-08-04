from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypeAlias

SpeechOutputPath: TypeAlias = str | Path


class SpeechBackend(ABC):
    """Interface for text-to-speech backends."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        output_path: SpeechOutputPath,
    ) -> None:
        """
        Synthesize text into a WAV file at output_path.

        Implementations should overwrite output_path when appropriate
        and raise a backend-specific speech error when synthesis fails.
        """
        raise NotImplementedError
