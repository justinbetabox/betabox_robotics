from __future__ import annotations

import math
import struct
import unittest

from betabox_robotics.audio.tones import (
    BYTES_PER_SAMPLE,
    DEFAULT_SAMPLE_RATE,
    MAX_PCM_AMPLITUDE,
    NOTE_FREQUENCIES,
    generate_silence,
    generate_tone,
    note_frequency,
)


class NoteFrequencyTests(unittest.TestCase):
    def test_returns_frequency_for_named_note(
        self,
    ) -> None:
        self.assertEqual(
            note_frequency("A4"),
            440.0,
        )

    def test_note_names_are_case_insensitive(
        self,
    ) -> None:
        self.assertEqual(
            note_frequency("c4"),
            NOTE_FREQUENCIES["C4"],
        )

    def test_note_names_allow_surrounding_whitespace(
        self,
    ) -> None:
        self.assertEqual(
            note_frequency("  A4  "),
            440.0,
        )

    def test_returns_frequency_for_sharp_note(
        self,
    ) -> None:
        self.assertEqual(
            note_frequency("C#4"),
            NOTE_FREQUENCIES["C#4"],
        )

    def test_flat_aliases_resolve_to_equivalent_sharps(
        self,
    ) -> None:
        aliases = {
            "Db4": "C#4",
            "Eb4": "D#4",
            "Gb4": "F#4",
            "Ab4": "G#4",
            "Bb4": "A#4",
        }

        for flat, sharp in aliases.items():
            with self.subTest(
                flat=flat,
                sharp=sharp,
            ):
                self.assertEqual(
                    note_frequency(flat),
                    NOTE_FREQUENCIES[sharp],
                )

    def test_flat_aliases_are_case_insensitive(
        self,
    ) -> None:
        self.assertEqual(
            note_frequency("bb3"),
            NOTE_FREQUENCIES["A#3"],
        )

    def test_accepts_integer_frequency(
        self,
    ) -> None:
        self.assertEqual(
            note_frequency(440),
            440.0,
        )

    def test_accepts_float_frequency(
        self,
    ) -> None:
        self.assertEqual(
            note_frequency(432.5),
            432.5,
        )

    def test_rejects_empty_note(
        self,
    ) -> None:
        for note in (
            "",
            " ",
            "\t",
            "\n",
        ):
            with (
                self.subTest(note=note),
                self.assertRaisesRegex(
                    ValueError,
                    "note cannot be empty",
                ),
            ):
                note_frequency(note)

    def test_rejects_unknown_note(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "unknown note",
        ):
            note_frequency("H4")

    def test_rejects_unknown_flat_note(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "unknown note",
        ):
            note_frequency("Cb4")

    def test_rejects_boolean_frequency(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "frequency must be a number",
        ):
            note_frequency(True)

    def test_rejects_non_numeric_frequency(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "frequency must be a number",
        ):
            note_frequency(
                object()  # type: ignore[arg-type]
            )

    def test_rejects_non_finite_frequency(
        self,
    ) -> None:
        for frequency in (
            math.nan,
            math.inf,
            -math.inf,
        ):
            with (
                self.subTest(
                    frequency=frequency,
                ),
                self.assertRaisesRegex(
                    ValueError,
                    "frequency must be finite",
                ),
            ):
                note_frequency(frequency)

    def test_rejects_non_positive_frequency(
        self,
    ) -> None:
        for frequency in (
            0,
            -1,
            -440.0,
        ):
            with (
                self.subTest(
                    frequency=frequency,
                ),
                self.assertRaisesRegex(
                    ValueError,
                    "frequency must be greater than 0",
                ),
            ):
                note_frequency(frequency)

    def test_frequency_mapping_is_read_only(
        self,
    ) -> None:
        with self.assertRaises(TypeError):
            NOTE_FREQUENCIES["A4"] = 441.0  # type: ignore[index]


class GenerateToneTests(unittest.TestCase):
    def test_generates_expected_number_of_bytes(
        self,
    ) -> None:
        sample_rate = 1000
        duration = 0.25

        data = generate_tone(
            100,
            duration,
            sample_rate=sample_rate,
        )

        expected_frames = int(sample_rate * duration)

        self.assertEqual(
            len(data),
            expected_frames * BYTES_PER_SAMPLE,
        )

    def test_uses_default_sample_rate(
        self,
    ) -> None:
        duration = 0.01

        data = generate_tone(
            440,
            duration,
        )

        self.assertEqual(
            len(data),
            int(DEFAULT_SAMPLE_RATE * duration) * BYTES_PER_SAMPLE,
        )

    def test_zero_duration_returns_empty_bytes(
        self,
    ) -> None:
        self.assertEqual(
            generate_tone(
                440,
                0,
            ),
            b"",
        )

    def test_first_pcm_sample_is_zero(
        self,
    ) -> None:
        data = generate_tone(
            440,
            0.01,
        )

        first_sample = struct.unpack_from(
            "<h",
            data,
            0,
        )[0]

        self.assertEqual(
            first_sample,
            0,
        )

    def test_generates_little_endian_signed_16_bit_pcm(
        self,
    ) -> None:
        data = generate_tone(
            frequency=1,
            duration=0.5,
            sample_rate=4,
            volume=1.0,
        )

        samples = struct.unpack(
            "<2h",
            data,
        )

        self.assertEqual(
            samples[0],
            0,
        )
        self.assertEqual(
            samples[1],
            MAX_PCM_AMPLITUDE,
        )

    def test_zero_volume_generates_silence(
        self,
    ) -> None:
        data = generate_tone(
            440,
            0.01,
            volume=0,
        )

        self.assertEqual(
            data,
            bytes(len(data)),
        )

    def test_volume_scales_pcm_amplitude(
        self,
    ) -> None:
        full_volume = generate_tone(
            frequency=1,
            duration=0.5,
            sample_rate=4,
            volume=1.0,
        )

        half_volume = generate_tone(
            frequency=1,
            duration=0.5,
            sample_rate=4,
            volume=0.5,
        )

        full_sample = struct.unpack_from(
            "<h",
            full_volume,
            BYTES_PER_SAMPLE,
        )[0]

        half_sample = struct.unpack_from(
            "<h",
            half_volume,
            BYTES_PER_SAMPLE,
        )[0]

        self.assertEqual(
            full_sample,
            MAX_PCM_AMPLITUDE,
        )
        self.assertEqual(
            half_sample,
            int(MAX_PCM_AMPLITUDE * 0.5),
        )

    def test_accepts_note_frequency_result(
        self,
    ) -> None:
        frequency = note_frequency("A4")

        data = generate_tone(
            frequency,
            0.01,
        )

        self.assertGreater(
            len(data),
            0,
        )

    def test_rejects_boolean_frequency(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "frequency must be a number",
        ):
            generate_tone(
                True,
                1,
            )

    def test_rejects_non_finite_frequency(
        self,
    ) -> None:
        for frequency in (
            math.nan,
            math.inf,
            -math.inf,
        ):
            with (
                self.subTest(
                    frequency=frequency,
                ),
                self.assertRaisesRegex(
                    ValueError,
                    "frequency must be finite",
                ),
            ):
                generate_tone(
                    frequency,
                    1,
                )

    def test_rejects_non_positive_frequency(
        self,
    ) -> None:
        for frequency in (
            0,
            -1,
        ):
            with (
                self.subTest(
                    frequency=frequency,
                ),
                self.assertRaisesRegex(
                    ValueError,
                    "frequency must be greater than 0",
                ),
            ):
                generate_tone(
                    frequency,
                    1,
                )

    def test_rejects_boolean_duration(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "duration must be a number",
        ):
            generate_tone(
                440,
                True,
            )

    def test_rejects_non_numeric_duration(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "duration must be a number",
        ):
            generate_tone(
                440,
                "one",  # type: ignore[arg-type]
            )

    def test_rejects_non_finite_duration(
        self,
    ) -> None:
        for duration in (
            math.nan,
            math.inf,
            -math.inf,
        ):
            with (
                self.subTest(
                    duration=duration,
                ),
                self.assertRaisesRegex(
                    ValueError,
                    "duration must be finite",
                ),
            ):
                generate_tone(
                    440,
                    duration,
                )

    def test_rejects_negative_duration(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "duration cannot be negative",
        ):
            generate_tone(
                440,
                -0.1,
            )

    def test_rejects_boolean_sample_rate(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "sample_rate must be an integer",
        ):
            generate_tone(
                440,
                1,
                sample_rate=True,
            )

    def test_rejects_non_integer_sample_rate(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "sample_rate must be an integer",
        ):
            generate_tone(
                440,
                1,
                sample_rate=44_100.5,  # type: ignore[arg-type]
            )

    def test_rejects_non_positive_sample_rate(
        self,
    ) -> None:
        for sample_rate in (
            0,
            -1,
        ):
            with (
                self.subTest(
                    sample_rate=sample_rate,
                ),
                self.assertRaisesRegex(
                    ValueError,
                    "sample_rate must be greater than 0",
                ),
            ):
                generate_tone(
                    440,
                    1,
                    sample_rate=sample_rate,
                )

    def test_rejects_boolean_volume(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "volume must be a number",
        ):
            generate_tone(
                440,
                1,
                volume=True,
            )

    def test_rejects_non_numeric_volume(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "volume must be a number",
        ):
            generate_tone(
                440,
                1,
                volume="loud",  # type: ignore[arg-type]
            )

    def test_rejects_non_finite_volume(
        self,
    ) -> None:
        for volume in (
            math.nan,
            math.inf,
            -math.inf,
        ):
            with (
                self.subTest(
                    volume=volume,
                ),
                self.assertRaisesRegex(
                    ValueError,
                    "volume must be finite",
                ),
            ):
                generate_tone(
                    440,
                    1,
                    volume=volume,
                )

    def test_rejects_volume_outside_range(
        self,
    ) -> None:
        for volume in (
            -0.01,
            1.01,
            50,
        ):
            with (
                self.subTest(
                    volume=volume,
                ),
                self.assertRaisesRegex(
                    ValueError,
                    "volume must be between 0.0 and 1.0",
                ),
            ):
                generate_tone(
                    440,
                    1,
                    volume=volume,
                )


class GenerateSilenceTests(unittest.TestCase):
    def test_generates_expected_number_of_zero_bytes(
        self,
    ) -> None:
        sample_rate = 1000
        duration = 0.25

        data = generate_silence(
            duration,
            sample_rate=sample_rate,
        )

        expected_length = int(sample_rate * duration) * BYTES_PER_SAMPLE

        self.assertEqual(
            len(data),
            expected_length,
        )
        self.assertEqual(
            data,
            bytes(expected_length),
        )

    def test_uses_default_sample_rate(
        self,
    ) -> None:
        duration = 0.01

        data = generate_silence(
            duration,
        )

        self.assertEqual(
            len(data),
            int(DEFAULT_SAMPLE_RATE * duration) * BYTES_PER_SAMPLE,
        )

    def test_zero_duration_returns_empty_bytes(
        self,
    ) -> None:
        self.assertEqual(
            generate_silence(0),
            b"",
        )

    def test_rejects_boolean_duration(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "duration must be a number",
        ):
            generate_silence(True)

    def test_rejects_non_numeric_duration(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "duration must be a number",
        ):
            generate_silence(
                "one",  # type: ignore[arg-type]
            )

    def test_rejects_non_finite_duration(
        self,
    ) -> None:
        for duration in (
            math.nan,
            math.inf,
            -math.inf,
        ):
            with (
                self.subTest(
                    duration=duration,
                ),
                self.assertRaisesRegex(
                    ValueError,
                    "duration must be finite",
                ),
            ):
                generate_silence(duration)

    def test_rejects_negative_duration(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "duration cannot be negative",
        ):
            generate_silence(-0.1)

    def test_rejects_boolean_sample_rate(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "sample_rate must be an integer",
        ):
            generate_silence(
                1,
                sample_rate=True,
            )

    def test_rejects_non_integer_sample_rate(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "sample_rate must be an integer",
        ):
            generate_silence(
                1,
                sample_rate=44_100.5,  # type: ignore[arg-type]
            )

    def test_rejects_non_positive_sample_rate(
        self,
    ) -> None:
        for sample_rate in (
            0,
            -1,
        ):
            with (
                self.subTest(
                    sample_rate=sample_rate,
                ),
                self.assertRaisesRegex(
                    ValueError,
                    "sample_rate must be greater than 0",
                ),
            ):
                generate_silence(
                    1,
                    sample_rate=sample_rate,
                )


if __name__ == "__main__":
    unittest.main()
