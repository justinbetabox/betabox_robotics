from abc import ABC, abstractmethod
from pathlib import Path


class SpeechBackend(ABC):
    """Interface for text-to-speech backends."""

    @abstractmethod
    def synthesize(self, text: str, output_path: str | Path) -> None:
        """
        Synthesize text into a WAV file at output_path.
        """
        pass
