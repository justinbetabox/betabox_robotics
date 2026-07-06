#!/usr/bin/env python3

from pathlib import Path

from betabox_robotics.audio import Audio, AudioError
from betabox_robotics.audio.pronunciation import prepare_speech_text
from betabox_robotics.audio.speech import SpeechBackend, available_backends
from betabox_robotics.audio.tones import note_frequency


class FakeSpeechBackend(SpeechBackend):
    def synthesize(self, text: str, output_path: str | Path) -> None:
        Path(output_path).write_bytes(b"fake wav")


class FakeAudio(Audio):
    def __init__(self) -> None:
        self.speech_backend = FakeSpeechBackend()
        self.speech_volume = 1.0
        self.played_sounds: list[str | Path] = []
        self.played_wavs: list[str | Path] = []
        self.closed = False

    def play_sound(self, sound: str | Path) -> None:
        self.played_sounds.append(sound)

    def play_wav(self, sound: str | Path, *, volume: float = 1.0) -> None:
        self.played_wavs.append(sound)

    def close(self) -> None:
        self.closed = True


def test_audio_play_delegates_to_play_sound():
    audio = FakeAudio()
    audio.play("car-honk")
    assert audio.played_sounds == ["car-honk"]


def test_audio_say_rejects_empty_text():
    audio = FakeAudio()

    try:
        audio.say("")
        raise AssertionError("expected AudioError")
    except AudioError:
        pass


def test_audio_say_uses_speech_backend_and_play_wav():
    audio = FakeAudio()
    audio.say("Hello")
    assert len(audio.played_wavs) == 1


def test_pronunciation_replaces_brand_name():
    prepared = prepare_speech_text("Hello from Betabox")
    assert "Betabox" not in prepared


def test_note_frequency_supports_sharps_flats_and_numbers():
    assert note_frequency("C5") == 523.25
    assert note_frequency("Bb4") == note_frequency("A#4")
    assert note_frequency(440.0) == 440.0


def test_note_frequency_rejects_unknown_note():
    try:
        note_frequency("H5")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_audio_missing_sound_raises_error():
    audio = Audio.__new__(Audio)

    try:
        Audio._resolve_sound_path(audio, "/tmp/does_not_exist.wav")
        raise AssertionError("expected AudioError")
    except AudioError:
        pass


def test_available_speech_backends_returns_list():
    backends = available_backends()
    assert isinstance(backends, list)


def test_audio_available_speech_backends_returns_list():
    audio = FakeAudio()
    backends = audio.available_speech_backends()
    assert isinstance(backends, list)


def test_audio_context_manager_closes():
    audio = FakeAudio()

    with audio:
        pass

    assert audio.closed is True


if __name__ == "__main__":
    test_audio_play_delegates_to_play_sound()
    test_audio_say_rejects_empty_text()
    test_audio_say_uses_speech_backend_and_play_wav()
    test_pronunciation_replaces_brand_name()
    test_note_frequency_supports_sharps_flats_and_numbers()
    test_note_frequency_rejects_unknown_note()
    test_audio_missing_sound_raises_error()
    test_available_speech_backends_returns_list()
    test_audio_available_speech_backends_returns_list()
    test_audio_context_manager_closes()

    print("\nAudio tests complete.")
