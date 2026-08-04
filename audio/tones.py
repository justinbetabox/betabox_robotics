from __future__ import annotations

import math
import struct
from collections.abc import Mapping
from types import MappingProxyType
from typing import Final, TypeAlias

NoteValue: TypeAlias = str | float | int
MelodyNote: TypeAlias = tuple[NoteValue, float]

DEFAULT_SAMPLE_RATE: Final[int] = 44_100
MAX_PCM_AMPLITUDE: Final[int] = 32_767
BYTES_PER_SAMPLE: Final[int] = 2


_NOTE_FREQUENCIES: dict[str, float] = {
    "C0": 16.35,
    "C#0": 17.32,
    "D0": 18.35,
    "D#0": 19.45,
    "E0": 20.60,
    "F0": 21.83,
    "F#0": 23.12,
    "G0": 24.50,
    "G#0": 25.96,
    "A0": 27.50,
    "A#0": 29.14,
    "B0": 30.87,
    "C1": 32.70,
    "C#1": 34.65,
    "D1": 36.71,
    "D#1": 38.89,
    "E1": 41.20,
    "F1": 43.65,
    "F#1": 46.25,
    "G1": 49.00,
    "G#1": 51.91,
    "A1": 55.00,
    "A#1": 58.27,
    "B1": 61.74,
    "C2": 65.41,
    "C#2": 69.30,
    "D2": 73.42,
    "D#2": 77.78,
    "E2": 82.41,
    "F2": 87.31,
    "F#2": 92.50,
    "G2": 98.00,
    "G#2": 103.83,
    "A2": 110.00,
    "A#2": 116.54,
    "B2": 123.47,
    "C3": 130.81,
    "C#3": 138.59,
    "D3": 146.83,
    "D#3": 155.56,
    "E3": 164.81,
    "F3": 174.61,
    "F#3": 185.00,
    "G3": 196.00,
    "G#3": 207.65,
    "A3": 220.00,
    "A#3": 233.08,
    "B3": 246.94,
    "C4": 261.63,
    "C#4": 277.18,
    "D4": 293.66,
    "D#4": 311.13,
    "E4": 329.63,
    "F4": 349.23,
    "F#4": 369.99,
    "G4": 392.00,
    "G#4": 415.30,
    "A4": 440.00,
    "A#4": 466.16,
    "B4": 493.88,
    "C5": 523.25,
    "C#5": 554.37,
    "D5": 587.33,
    "D#5": 622.25,
    "E5": 659.26,
    "F5": 698.46,
    "F#5": 739.99,
    "G5": 783.99,
    "G#5": 830.61,
    "A5": 880.00,
    "A#5": 932.33,
    "B5": 987.77,
    "C6": 1046.50,
    "C#6": 1108.73,
    "D6": 1174.66,
    "D#6": 1244.51,
    "E6": 1318.51,
    "F6": 1396.91,
    "F#6": 1479.98,
    "G6": 1567.98,
    "G#6": 1661.22,
    "A6": 1760.00,
    "A#6": 1864.66,
    "B6": 1975.53,
    "C7": 2093.00,
    "C#7": 2217.46,
    "D7": 2349.32,
    "D#7": 2489.02,
    "E7": 2637.02,
    "F7": 2793.83,
    "F#7": 2959.96,
    "G7": 3135.96,
    "G#7": 3322.44,
    "A7": 3520.00,
    "A#7": 3729.31,
    "B7": 3951.07,
    "C8": 4186.01,
    "C#8": 4434.92,
    "D8": 4698.63,
    "D#8": 4978.03,
    "E8": 5274.04,
    "F8": 5587.65,
    "F#8": 5919.91,
    "G8": 6271.93,
    "G#8": 6644.88,
    "A8": 7040.00,
    "A#8": 7458.62,
    "B8": 7902.13,
}

NOTE_FREQUENCIES: Mapping[str, float] = MappingProxyType(_NOTE_FREQUENCIES)

FLAT_ALIASES: Mapping[str, str] = MappingProxyType(
    {
        "DB": "C#",
        "EB": "D#",
        "GB": "F#",
        "AB": "G#",
        "BB": "A#",
    }
)


def _require_finite_number(
    value: object,
    *,
    name: str,
) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        int | float,
    ):
        raise TypeError(f"{name} must be a number")

    result = float(value)

    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")

    return result


def _require_sample_rate(
    sample_rate: object,
) -> int:
    if isinstance(sample_rate, bool) or not isinstance(
        sample_rate,
        int,
    ):
        raise TypeError("sample_rate must be an integer")

    if sample_rate <= 0:
        raise ValueError("sample_rate must be greater than 0")

    return sample_rate


def _normalize_note_name(
    note: str,
) -> str:
    normalized = note.strip().upper()

    if not normalized:
        raise ValueError("note cannot be empty")

    if len(normalized) >= 3 and normalized[1] == "B":
        pitch = normalized[:2]
        octave = normalized[2:]

        alias = FLAT_ALIASES.get(pitch)

        if alias is not None:
            normalized = f"{alias}{octave}"

    return normalized


def note_frequency(
    note_or_frequency: NoteValue,
) -> float:
    if isinstance(note_or_frequency, str):
        note = _normalize_note_name(note_or_frequency)

        frequency = NOTE_FREQUENCIES.get(note)

        if frequency is None:
            raise ValueError(f"unknown note: {note_or_frequency}")

        return frequency

    frequency = _require_finite_number(
        note_or_frequency,
        name="frequency",
    )

    if frequency <= 0:
        raise ValueError("frequency must be greater than 0")

    return frequency


def generate_tone(
    frequency: float,
    duration: float,
    *,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    volume: float = 1.0,
) -> bytes:
    frequency_value = _require_finite_number(
        frequency,
        name="frequency",
    )
    duration_value = _require_finite_number(
        duration,
        name="duration",
    )
    volume_value = _require_finite_number(
        volume,
        name="volume",
    )
    sample_rate_value = _require_sample_rate(sample_rate)

    if frequency_value <= 0:
        raise ValueError("frequency must be greater than 0")

    if duration_value < 0:
        raise ValueError("duration cannot be negative")

    if not 0.0 <= volume_value <= 1.0:
        raise ValueError("volume must be between 0.0 and 1.0")

    frames = int(sample_rate_value * duration_value)

    data = bytearray(frames * BYTES_PER_SAMPLE)

    for index in range(frames):
        value = math.sin(2.0 * math.pi * frequency_value * index / sample_rate_value)

        sample = int(MAX_PCM_AMPLITUDE * volume_value * value)

        struct.pack_into(
            "<h",
            data,
            index * BYTES_PER_SAMPLE,
            sample,
        )

    return bytes(data)


def generate_silence(
    duration: float,
    *,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> bytes:
    duration_value = _require_finite_number(
        duration,
        name="duration",
    )
    sample_rate_value = _require_sample_rate(sample_rate)

    if duration_value < 0:
        raise ValueError("duration cannot be negative")

    frames = int(sample_rate_value * duration_value)

    return bytes(frames * BYTES_PER_SAMPLE)
