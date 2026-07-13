from __future__ import annotations

from betabox_robotics.audio import (
    Audio,
    AudioError,
    AudioStatus,
    MelodyNote,
)

from betabox_robotics.robots import BETABOX_CAR

def main() -> None:
    print()
    print("Betabox Audio API Test")
    print("======================")
    print()

    audio = Audio.default(BETABOX_CAR.audio)

    status = audio.status()
    assert isinstance(status, AudioStatus)
    assert status.closed is False
    assert status.playing is False
    assert status.sample_rate > 0

    assert isinstance(audio.speech_backend_name, str)
    assert isinstance(audio.available_speech_backends(), list)

    notes: list[MelodyNote] = [
        ("C4", 0.1),
        ("E4", 0.1),
        ("G4", 0.1),
    ]

    audio.play_note("A4", 0.1)
    audio.play_note(440, 0.1)
    audio.play_melody(notes, gap=0.02)

    try:
        audio.play_note("A4", 0)
    except AudioError:
        pass
    else:
        raise AssertionError("zero-duration note was accepted")

    try:
        audio.play_melody([("C4", -1.0)])
    except AudioError:
        pass
    else:
        raise AssertionError("negative melody duration was accepted")

    audio.close()
    audio.close()

    closed_status = audio.status()
    assert closed_status.closed is True
    assert closed_status.playing is False

    try:
        audio.play_note("A4", 0.1)
    except AudioError:
        pass
    else:
        raise AssertionError("closed audio subsystem accepted playback")

    print("Audio API test passed.")
    print()


if __name__ == "__main__":
    main()
