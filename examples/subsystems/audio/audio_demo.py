#!/usr/bin/env python3
"""
Betabox Audio subsystem developer demo.

Exercises speech, sound playback, tones, and melodies through the
configured Audio subsystem.

This demo validates:

- Audio.default();
- configured speech backend selection;
- output-device discovery;
- status reporting;
- single-note playback;
- melody playback;
- packaged sound playback;
- speech synthesis and playback;
- amplifier lifecycle management;
- context-managed cleanup.

Ensure the robot speaker is connected before running this demo.
The demo produces several sounds at normal listening volume.
"""

from __future__ import annotations

from betabox_robotics.audio import (
    Audio,
    AudioError,
)
from betabox_robotics.robots import BETABOX_CAR

DEMO_SOUND = "car-honk"
DEMO_TEXT = "Hello from Betabox"

NOTE_DURATION = 0.5
MELODY_GAP = 0.05

DEMO_MELODY = [
    (
        "C5",
        0.2,
    ),
    (
        "D5",
        0.2,
    ),
    (
        "E5",
        0.2,
    ),
    (
        "G5",
        0.4,
    ),
]


def print_status(
    label: str,
    audio: Audio,
) -> None:
    status = audio.status()

    print()
    print(label)
    print("-" * len(label))
    print(f"Speech backend:    {status.backend}")
    print(
        "Available backends: "
        + (", ".join(status.available_backends) if status.available_backends else "-")
    )
    print(
        "Output device index: "
        + (
            str(status.output_device_index)
            if status.output_device_index is not None
            else "-"
        )
    )
    print(f"Sample rate:       {status.sample_rate} Hz")
    print(f"Automatic amp:     {status.auto_amp}")
    print(f"Keep amp enabled:  {status.keep_amp_enabled}")
    print(f"Playing:           {status.playing}")
    print(f"Closed:            {status.closed}")


def run_tone_demo(
    audio: Audio,
) -> None:
    print()
    print("Tone playback")
    print("-------------")
    print(f"Playing C5 for {NOTE_DURATION:.1f} seconds...")

    audio.play_note(
        "C5",
        NOTE_DURATION,
    )


def run_melody_demo(
    audio: Audio,
) -> None:
    print()
    print("Melody playback")
    print("---------------")
    print("Playing C5, D5, E5, and G5...")

    audio.play_melody(
        DEMO_MELODY,
        gap=MELODY_GAP,
    )


def run_sound_demo(
    audio: Audio,
) -> None:
    print()
    print("Sound playback")
    print("--------------")
    print(f"Playing packaged sound: {DEMO_SOUND}")

    audio.play(DEMO_SOUND)


def run_speech_demo(
    audio: Audio,
) -> None:
    print()
    print("Speech")
    print("------")
    print(f'Speaking: "{DEMO_TEXT}"')

    audio.say(DEMO_TEXT)


def main() -> int:
    print()
    print("Betabox Audio demo")
    print("==================")
    print()
    print("This demo plays a tone, a melody, a packaged sound, and synthesized speech.")
    print("Press Ctrl+C at any time to stop the demo.")

    cleanup_audio: Audio | None = None

    try:
        audio = Audio.default(
            BETABOX_CAR.audio,
        )
        cleanup_audio = audio

        with audio:
            print_status(
                "Initial status",
                audio,
            )

            run_tone_demo(audio)
            run_melody_demo(audio)
            run_sound_demo(audio)
            run_speech_demo(audio)

            print_status(
                "Final status",
                audio,
            )

        print()
        print(f"Closed after context exit: {audio.closed}")

    except KeyboardInterrupt:
        print()
        print("Audio demo interrupted.")
        return 130

    except AudioError as exc:
        print()
        print(f"Audio demo failed: {exc}")
        return 1

    except (
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        print()
        print(f"Audio demo failed: {type(exc).__name__}: {exc}")
        return 1

    finally:
        if cleanup_audio is not None and not cleanup_audio.closed:
            cleanup_audio.close()

    print()
    print("Audio demo complete.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
