#!/usr/bin/env python3
"""
Developer demo for the Betabox Audio subsystem.
"""

from betabox_car.audio import Audio, AudioError


def main() -> None:
    print()
    print("Betabox Audio Demo")
    print("==================")
    print()

    try:
        with Audio(
            keep_amp_enabled=True,
            speech_engine="pico",
            speech_volume=1.8,
        ) as audio:
            print(f"Speech backend: {audio.speech_backend_name}")
            print(f"Available speech backends: {audio.available_speech_backends()}")
            print()

            print("Playing note...")
            audio.play_note("C5", 0.5)

            print("Playing melody...")
            audio.play_melody(
                [
                    ("C5", 0.2),
                    ("D5", 0.2),
                    ("E5", 0.2),
                    ("G5", 0.4),
                ],
                gap=0.05,
            )

            print("Playing sound...")
            audio.play_sound("car-honk")

            print("Speaking...")
            audio.say("Hello from Betabox")

    except AudioError as exc:
        print(f"Audio error: {exc}")

    print()
    print("Audio demo complete.")


if __name__ == "__main__":
    main()
