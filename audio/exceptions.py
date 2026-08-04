class AudioError(Exception):
    """Base exception for audio operations."""


class SpeechError(AudioError):
    """Raised when speech synthesis fails."""


class PlaybackError(AudioError):
    """Raised when audio playback fails."""


class AmplifierError(AudioError):
    """Raised when amplifier control fails."""
