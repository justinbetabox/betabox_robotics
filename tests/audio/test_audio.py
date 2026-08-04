from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pyaudio

from betabox_robotics.audio.audio import (
    AUDIO_CONVERSION_TIMEOUT_SECONDS,
    DEFAULT_OUTPUT_DEVICE,
    DEFAULT_SAMPLE_RATE,
    MAX_PLAYBACK_VOLUME,
    Audio,
    AudioStatus,
    _require_finite_number,
    _require_nonempty_string,
    _require_positive_integer,
    _require_volume,
)
from betabox_robotics.audio.exceptions import (
    AudioError,
    PlaybackError,
)
from betabox_robotics.audio.speech import SpeechBackend


class FakeSpeechBackend(SpeechBackend):
    name = "fake"

    def __init__(self) -> None:
        self.calls: list[tuple[str, Path]] = []

    def synthesize(
        self,
        text: str,
        output_path: str | Path,
    ) -> None:
        path = Path(output_path)
        self.calls.append(
            (
                text,
                path,
            )
        )

        with wave.open(
            str(path),
            "wb",
        ) as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(DEFAULT_SAMPLE_RATE)
            wav.writeframes(b"\x00\x00" * 8)


class FakeStream:
    def __init__(self) -> None:
        self.writes: list[bytes] = []
        self.stop_count = 0
        self.close_count = 0
        self.write_error: OSError | RuntimeError | None = None
        self.stop_error: OSError | RuntimeError | None = None
        self.close_error: OSError | RuntimeError | None = None

    def write(
        self,
        data: bytes,
    ) -> None:
        if self.write_error is not None:
            raise self.write_error

        self.writes.append(data)

    def stop_stream(self) -> None:
        self.stop_count += 1

        if self.stop_error is not None:
            raise self.stop_error

    def close(self) -> None:
        self.close_count += 1

        if self.close_error is not None:
            raise self.close_error


class FakePyAudio:
    def __init__(self) -> None:
        self.stream = FakeStream()
        self.open_calls: list[dict[str, object]] = []
        self.terminate_count = 0
        self.device_infos: list[dict[str, object]] = [
            {
                "index": 0,
                "name": "input only",
                "maxOutputChannels": 0,
            },
            {
                "index": 1,
                "name": "snd_rpi_hifiberry_dac",
                "maxOutputChannels": 2,
            },
        ]
        self.default_device_info: dict[str, object] = {
            "index": 1,
            "name": "snd_rpi_hifiberry_dac",
            "maxOutputChannels": 2,
        }
        self.open_error: OSError | RuntimeError | TypeError | ValueError | None = None
        self.terminate_error: OSError | RuntimeError | None = None

    def get_device_count(self) -> int:
        return len(self.device_infos)

    def get_device_info_by_index(
        self,
        index: int,
    ) -> dict[str, object]:
        return self.device_infos[index]

    def get_default_output_device_info(
        self,
    ) -> dict[str, object]:
        return self.default_device_info

    def open(
        self,
        **kwargs: object,
    ) -> FakeStream:
        if self.open_error is not None:
            raise self.open_error

        self.open_calls.append(kwargs)
        return self.stream

    def terminate(self) -> None:
        self.terminate_count += 1

        if self.terminate_error is not None:
            raise self.terminate_error


def make_audio(
    *,
    backend: SpeechBackend | None = None,
    preferred_output_device: str = DEFAULT_OUTPUT_DEVICE,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    auto_amp: bool = False,
    keep_amp_enabled: bool = False,
    speech_volume: float = 1.0,
) -> tuple[
    Audio,
    FakePyAudio,
]:
    fake_pyaudio = FakePyAudio()

    with patch(
        "betabox_robotics.audio.audio.pyaudio.PyAudio",
        return_value=fake_pyaudio,
    ):
        audio = Audio(
            speech_backend=backend or FakeSpeechBackend(),
            preferred_output_device=preferred_output_device,
            sample_rate=sample_rate,
            auto_amp=auto_amp,
            keep_amp_enabled=keep_amp_enabled,
            speech_volume=speech_volume,
        )

    return (
        audio,
        fake_pyaudio,
    )


def write_pcm16_wav(
    path: Path,
    *,
    channels: int = 1,
    sample_rate: int = 8_000,
    frames: bytes = b"\x01\x00\x02\x00",
) -> None:
    with wave.open(
        str(path),
        "wb",
    ) as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(frames)


class AudioStatusTests(unittest.TestCase):
    def test_to_dict_returns_all_fields(
        self,
    ) -> None:
        status = AudioStatus(
            backend="fake",
            available_backends=[
                "fake",
            ],
            output_device_index=1,
            sample_rate=44_100,
            auto_amp=True,
            keep_amp_enabled=False,
            playing=False,
            closed=False,
        )

        self.assertEqual(
            status.to_dict(),
            {
                "backend": "fake",
                "available_backends": [
                    "fake",
                ],
                "output_device_index": 1,
                "sample_rate": 44_100,
                "auto_amp": True,
                "keep_amp_enabled": False,
                "playing": False,
                "closed": False,
            },
        )


class AudioValidationTests(unittest.TestCase):
    def test_nonempty_string_validation(
        self,
    ) -> None:
        self.assertEqual(
            _require_nonempty_string(
                "  hello  ",
                name="value",
            ),
            "hello",
        )

        with self.assertRaisesRegex(
            TypeError,
            "value must be a string",
        ):
            _require_nonempty_string(
                1,
                name="value",
            )

        with self.assertRaisesRegex(
            ValueError,
            "value cannot be empty",
        ):
            _require_nonempty_string(
                " ",
                name="value",
            )

    def test_positive_integer_validation(
        self,
    ) -> None:
        self.assertEqual(
            _require_positive_integer(
                44_100,
                name="sample_rate",
            ),
            44_100,
        )

        for value in (
            True,
            44_100.0,
            "44100",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "sample_rate must be an integer",
                ),
            ):
                _require_positive_integer(
                    value,
                    name="sample_rate",
                )

        with self.assertRaisesRegex(
            ValueError,
            "sample_rate must be greater than 0",
        ):
            _require_positive_integer(
                0,
                name="sample_rate",
            )

    def test_finite_number_validation(
        self,
    ) -> None:
        self.assertEqual(
            _require_finite_number(
                1,
                name="value",
            ),
            1.0,
        )

        with self.assertRaisesRegex(
            TypeError,
            "value must be a number",
        ):
            _require_finite_number(
                True,
                name="value",
            )

        for value in (
            float("nan"),
            float("inf"),
            float("-inf"),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "value must be finite",
                ),
            ):
                _require_finite_number(
                    value,
                    name="value",
                )

    def test_volume_validation(
        self,
    ) -> None:
        for volume in (
            0,
            1.0,
            MAX_PLAYBACK_VOLUME,
        ):
            with self.subTest(volume=volume):
                self.assertEqual(
                    _require_volume(
                        volume,
                        name="volume",
                    ),
                    float(volume),
                )

        for volume in (
            -0.1,
            MAX_PLAYBACK_VOLUME + 0.1,
        ):
            with (
                self.subTest(volume=volume),
                self.assertRaisesRegex(
                    ValueError,
                    "volume must be between",
                ),
            ):
                _require_volume(
                    volume,
                    name="volume",
                )


class AudioConstructionTests(unittest.TestCase):
    def test_constructor_stores_configuration_and_finds_device(
        self,
    ) -> None:
        backend = FakeSpeechBackend()
        audio, fake_pyaudio = make_audio(
            backend=backend,
            sample_rate=22_050,
            speech_volume=1.5,
        )

        self.assertIs(
            audio.speech_backend,
            backend,
        )
        self.assertEqual(
            audio.sample_rate,
            22_050,
        )
        self.assertEqual(
            audio.speech_volume,
            1.5,
        )
        self.assertEqual(
            audio._device_index,
            1,
        )
        self.assertFalse(audio.closed)
        self.assertFalse(audio.is_playing())
        self.assertEqual(
            fake_pyaudio.terminate_count,
            0,
        )

    def test_environment_device_overrides_constructor_value(
        self,
    ) -> None:
        with patch.dict(
            os.environ,
            {
                "BETABOX_AUDIO_DEVICE": "usb audio",
            },
        ):
            audio, _ = make_audio(
                preferred_output_device="ignored",
            )

        self.assertEqual(
            audio.preferred_output_device,
            "usb audio",
        )

    def test_constructor_validates_configuration(
        self,
    ) -> None:
        invalid_cases = (
            (
                {
                    "auto_amp": 1,
                },
                TypeError,
                "auto_amp must be a boolean",
            ),
            (
                {
                    "keep_amp_enabled": 1,
                },
                TypeError,
                "keep_amp_enabled must be a boolean",
            ),
            (
                {
                    "preferred_output_device": 1,
                },
                TypeError,
                "preferred_output_device must be a string",
            ),
            (
                {
                    "sample_rate": 0,
                },
                ValueError,
                "sample_rate must be greater than 0",
            ),
            (
                {
                    "speech_volume": 4.0,
                },
                ValueError,
                "speech_volume must be between",
            ),
        )

        for kwargs, exception_type, message in invalid_cases:
            with (
                self.subTest(kwargs=kwargs),
                self.assertRaisesRegex(
                    exception_type,
                    message,
                ),
            ):
                Audio(
                    speech_backend=FakeSpeechBackend(),
                    **kwargs,  # type: ignore[arg-type]
                )

    def test_default_uses_audio_config(
        self,
    ) -> None:
        config = SimpleNamespace(
            speech_engine="pico",
            speech_language="en-GB",
            piper_model=Path("/tmp/model.onnx"),
            piper_voice="amy",
            preferred_output_device="device",
            sample_rate=22_050,
            auto_amp=False,
            keep_amp_enabled=False,
            speech_volume=1.25,
        )
        backend = FakeSpeechBackend()
        fake_pyaudio = FakePyAudio()

        with (
            patch(
                "betabox_robotics.audio.audio.create_backend",
                return_value=backend,
            ) as create,
            patch(
                "betabox_robotics.audio.audio.pyaudio.PyAudio",
                return_value=fake_pyaudio,
            ),
        ):
            audio = Audio.default(config)

        create.assert_called_once_with(
            speech_engine="pico",
            speech_language="en-GB",
            piper_model=Path("/tmp/model.onnx"),
            piper_voice="amy",
        )
        self.assertEqual(
            audio.sample_rate,
            22_050,
        )
        self.assertEqual(
            audio.preferred_output_device,
            "device",
        )

    def test_keep_amp_enabled_enables_speaker(
        self,
    ) -> None:
        with patch(
            "betabox_robotics.audio.audio.enable_speaker",
        ) as enable:
            audio, _ = make_audio(
                keep_amp_enabled=True,
            )

        enable.assert_called_once_with()
        audio.close()

    def test_initialization_failure_is_wrapped(
        self,
    ) -> None:
        with (
            patch(
                "betabox_robotics.audio.audio.pyaudio.PyAudio",
                side_effect=RuntimeError("portaudio failed"),
            ),
            self.assertRaisesRegex(
                PlaybackError,
                "failed to initialize audio output",
            ),
        ):
            Audio(
                speech_backend=FakeSpeechBackend(),
            )


class AudioSpeechTests(unittest.TestCase):
    def test_say_prepares_synthesizes_and_plays_speech(
        self,
    ) -> None:
        backend = FakeSpeechBackend()
        audio, _ = make_audio(
            backend=backend,
        )

        with (
            patch(
                "betabox_robotics.audio.audio.prepare_speech_text",
                return_value="prepared speech",
            ) as prepare,
            patch.object(
                audio,
                "play_wav",
            ) as play_wav,
        ):
            audio.say("  Hello  ")

        prepare.assert_called_once_with("Hello")
        self.assertEqual(
            len(backend.calls),
            1,
        )
        self.assertEqual(
            backend.calls[0][0],
            "prepared speech",
        )
        play_wav.assert_called_once()

        synthesized_path = backend.calls[0][1]
        self.assertFalse(
            synthesized_path.exists(),
        )

    def test_say_rejects_empty_text(
        self,
    ) -> None:
        audio, _ = make_audio()

        with self.assertRaisesRegex(
            ValueError,
            "text cannot be empty",
        ):
            audio.say(" ")

    def test_say_removes_processed_temporary_file(
        self,
    ) -> None:
        backend = FakeSpeechBackend()
        audio, _ = make_audio(
            backend=backend,
        )

        fd, temporary_name = tempfile.mkstemp(
            suffix=".wav",
        )
        os.close(fd)
        processed_path = Path(temporary_name)

        with (
            patch.object(
                audio,
                "_postprocess_speech",
                return_value=processed_path,
            ),
            patch.object(
                audio,
                "play_wav",
            ),
        ):
            audio.say("Hello")

        self.assertFalse(
            processed_path.exists(),
        )


class AudioPlaybackTests(unittest.TestCase):
    def test_play_delegates_to_play_sound(
        self,
    ) -> None:
        audio, _ = make_audio()

        with patch.object(
            audio,
            "play_sound",
        ) as play_sound:
            audio.play("sound")

        play_sound.assert_called_once_with("sound")

    def test_play_sound_converts_and_removes_temporary_file(
        self,
    ) -> None:
        audio, _ = make_audio()

        fd, source_name = tempfile.mkstemp(
            suffix=".mp3",
        )
        os.close(fd)
        source_path = Path(source_name)

        fd, wav_name = tempfile.mkstemp(
            suffix=".wav",
        )
        os.close(fd)
        wav_path = Path(wav_name)

        try:
            with (
                patch.object(
                    audio,
                    "_resolve_sound_path",
                    return_value=source_path,
                ),
                patch.object(
                    audio,
                    "_to_pcm16_wav",
                    return_value=(
                        wav_path,
                        True,
                    ),
                ),
                patch.object(
                    audio,
                    "play_wav",
                ) as play_wav,
            ):
                audio.play_sound("sound")

            play_wav.assert_called_once_with(wav_path)
            self.assertFalse(
                wav_path.exists(),
            )
        finally:
            source_path.unlink(
                missing_ok=True,
            )
            wav_path.unlink(
                missing_ok=True,
            )

    def test_play_wav_opens_stream_and_writes_frames(
        self,
    ) -> None:
        audio, fake_pyaudio = make_audio()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sound.wav"
            frames = b"\x01\x00\x02\x00"
            write_pcm16_wav(
                path,
                channels=1,
                sample_rate=8_000,
                frames=frames,
            )

            audio.play_wav(path)

        self.assertEqual(
            fake_pyaudio.open_calls,
            [
                {
                    "format": pyaudio.paInt16,
                    "channels": 1,
                    "rate": 8_000,
                    "output": True,
                    "output_device_index": 1,
                },
            ],
        )
        self.assertEqual(
            fake_pyaudio.stream.writes,
            [
                frames,
            ],
        )
        self.assertEqual(
            fake_pyaudio.stream.stop_count,
            1,
        )
        self.assertEqual(
            fake_pyaudio.stream.close_count,
            1,
        )
        self.assertFalse(audio.is_playing())

    def test_play_wav_scales_volume(
        self,
    ) -> None:
        audio, fake_pyaudio = make_audio()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sound.wav"
            write_pcm16_wav(
                path,
                frames=b"\xe8\x03",
            )

            audio.play_wav(
                path,
                volume=0.5,
            )

        self.assertEqual(
            fake_pyaudio.stream.writes,
            [
                b"\xf4\x01",
            ],
        )

    def test_play_wav_rejects_missing_file(
        self,
    ) -> None:
        audio, _ = make_audio()

        with self.assertRaisesRegex(
            PlaybackError,
            "sound file does not exist",
        ):
            audio.play_wav("/missing/sound.wav")

    def test_play_wav_rejects_non_pcm16_wav(
        self,
    ) -> None:
        audio, _ = make_audio()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sound.wav"

            with wave.open(
                str(path),
                "wb",
            ) as wav:
                wav.setnchannels(1)
                wav.setsampwidth(1)
                wav.setframerate(8_000)
                wav.writeframes(b"\x00")

            with self.assertRaisesRegex(
                PlaybackError,
                "only uncompressed 16-bit PCM WAV",
            ):
                audio.play_wav(path)

    def test_output_failure_is_wrapped(
        self,
    ) -> None:
        audio, fake_pyaudio = make_audio()
        fake_pyaudio.stream.write_error = RuntimeError("write failed")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sound.wav"
            write_pcm16_wav(path)

            with self.assertRaisesRegex(
                PlaybackError,
                "audio playback failed",
            ):
                audio.play_wav(path)


class AudioToneTests(unittest.TestCase):
    def test_play_note_generates_and_plays_tone(
        self,
    ) -> None:
        audio, _ = make_audio()

        with (
            patch(
                "betabox_robotics.audio.audio.note_frequency",
                return_value=440.0,
            ) as frequency,
            patch(
                "betabox_robotics.audio.audio.generate_tone",
                return_value=b"tone",
            ) as generate,
            patch.object(
                audio,
                "_play_pcm",
            ) as play_pcm,
        ):
            audio.play_note(
                "A4",
                0.5,
            )

        frequency.assert_called_once_with("A4")
        generate.assert_called_once_with(
            440.0,
            0.5,
            sample_rate=DEFAULT_SAMPLE_RATE,
        )
        play_pcm.assert_called_once_with(
            b"tone",
            channels=1,
            sample_rate=DEFAULT_SAMPLE_RATE,
        )

    def test_play_note_rejects_non_positive_duration(
        self,
    ) -> None:
        audio, _ = make_audio()

        for duration in (
            0,
            -0.1,
        ):
            with (
                self.subTest(duration=duration),
                self.assertRaisesRegex(
                    ValueError,
                    "duration must be greater than 0",
                ),
            ):
                audio.play_note(
                    "A4",
                    duration,
                )

    def test_play_melody_writes_tones_and_gap(
        self,
    ) -> None:
        audio, fake_pyaudio = make_audio()

        with (
            patch(
                "betabox_robotics.audio.audio.note_frequency",
                side_effect=[
                    440.0,
                    493.88,
                ],
            ),
            patch(
                "betabox_robotics.audio.audio.generate_tone",
                side_effect=[
                    b"tone-a",
                    b"tone-b",
                ],
            ),
            patch(
                "betabox_robotics.audio.audio.generate_silence",
                return_value=b"gap",
            ),
        ):
            audio.play_melody(
                [
                    (
                        "A4",
                        0.25,
                    ),
                    (
                        "B4",
                        0.5,
                    ),
                ],
                gap=0.1,
            )

        self.assertEqual(
            fake_pyaudio.stream.writes,
            [
                b"tone-a",
                b"gap",
                b"tone-b",
                b"gap",
            ],
        )

    def test_play_melody_returns_without_opening_stream_for_empty_list(
        self,
    ) -> None:
        audio, fake_pyaudio = make_audio()

        audio.play_melody([])

        self.assertEqual(
            fake_pyaudio.open_calls,
            [],
        )

    def test_play_melody_validates_input(
        self,
    ) -> None:
        audio, _ = make_audio()

        with self.assertRaisesRegex(
            TypeError,
            "notes must be a list",
        ):
            audio.play_melody(  # type: ignore[arg-type]
                (
                    (
                        "A4",
                        0.5,
                    ),
                )
            )

        with self.assertRaisesRegex(
            ValueError,
            "gap cannot be negative",
        ):
            audio.play_melody(
                [],
                gap=-0.1,
            )

        with self.assertRaisesRegex(
            ValueError,
            "melody note duration must be greater than 0",
        ):
            audio.play_melody(
                [
                    (
                        "A4",
                        0,
                    ),
                ]
            )


class AudioPathAndConversionTests(unittest.TestCase):
    def test_resolve_sound_path_checks_supported_extensions(
        self,
    ) -> None:
        audio, _ = make_audio()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "alert.ogg"
            path.touch()

            with patch(
                "betabox_robotics.audio.audio.Path.cwd",
                return_value=Path(directory),
            ):
                result = audio._resolve_sound_path("alert")

        self.assertEqual(
            result,
            path,
        )

    def test_pcm16_wav_is_returned_without_conversion(
        self,
    ) -> None:
        audio, _ = make_audio()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sound.wav"
            write_pcm16_wav(path)

            result, temporary = audio._to_pcm16_wav(path)

        self.assertEqual(
            result,
            path,
        )
        self.assertFalse(temporary)

    def test_conversion_uses_configured_sample_rate(
        self,
    ) -> None:
        audio, _ = make_audio(
            sample_rate=22_050,
        )

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sound.mp3"
            output = Path(directory) / "sound.wav"

            with patch(
                "betabox_robotics.audio.audio.shutil.which",
                side_effect=lambda command: (
                    "/usr/bin/ffmpeg" if command == "ffmpeg" else None
                ),
            ):
                command = audio._audio_conversion_command(
                    source_path=source,
                    output_path=output,
                )

        self.assertEqual(
            command,
            [
                "/usr/bin/ffmpeg",
                "-y",
                "-i",
                str(source),
                "-ac",
                "1",
                "-ar",
                "22050",
                "-c:a",
                "pcm_s16le",
                str(output),
            ],
        )

    def test_conversion_requires_ffmpeg_or_sox(
        self,
    ) -> None:
        audio, _ = make_audio()

        with (
            patch(
                "betabox_robotics.audio.audio.shutil.which",
                return_value=None,
            ),
            self.assertRaisesRegex(
                PlaybackError,
                "install ffmpeg or sox",
            ),
        ):
            audio._audio_conversion_command(
                source_path=Path("/tmp/source.mp3"),
                output_path=Path("/tmp/output.wav"),
            )

    def test_run_audio_command_wraps_expected_failures(
        self,
    ) -> None:
        cases = (
            (
                subprocess.TimeoutExpired(
                    [
                        "ffmpeg",
                    ],
                    AUDIO_CONVERSION_TIMEOUT_SECONDS,
                ),
                "timed out",
            ),
            (
                subprocess.CalledProcessError(
                    1,
                    [
                        "ffmpeg",
                    ],
                    stderr="conversion failed",
                ),
                "audio conversion failed: conversion failed",
            ),
            (
                OSError("missing executable"),
                "failed to start audio conversion",
            ),
        )

        for error, message in cases:
            with (
                self.subTest(error=error),
                patch(
                    "betabox_robotics.audio.audio.subprocess.run",
                    side_effect=error,
                ),
                self.assertRaisesRegex(
                    PlaybackError,
                    message,
                ),
            ):
                Audio._run_audio_command(
                    [
                        "ffmpeg",
                    ],
                    operation="audio conversion",
                    timeout=AUDIO_CONVERSION_TIMEOUT_SECONDS,
                )


class AudioStatusAndLifecycleTests(unittest.TestCase):
    def test_status_reports_current_state(
        self,
    ) -> None:
        audio, _ = make_audio(
            sample_rate=22_050,
            auto_amp=True,
        )

        with patch(
            "betabox_robotics.audio.audio.available_backends",
            return_value=[
                "pico2wave",
                "espeak-ng",
            ],
        ):
            status = audio.status()

        self.assertEqual(
            status,
            AudioStatus(
                backend="fake",
                available_backends=[
                    "pico2wave",
                    "espeak-ng",
                ],
                output_device_index=1,
                sample_rate=22_050,
                auto_amp=True,
                keep_amp_enabled=False,
                playing=False,
                closed=False,
            ),
        )

    def test_close_disables_speaker_and_terminates_audio(
        self,
    ) -> None:
        audio, fake_pyaudio = make_audio(
            auto_amp=True,
        )

        with patch(
            "betabox_robotics.audio.audio.disable_speaker",
        ) as disable:
            audio.close()

        disable.assert_called_once_with()
        self.assertEqual(
            fake_pyaudio.terminate_count,
            1,
        )
        self.assertTrue(audio.closed)
        self.assertFalse(audio._playing)

    def test_close_is_idempotent(
        self,
    ) -> None:
        audio, fake_pyaudio = make_audio()

        audio.close()
        audio.close()

        self.assertEqual(
            fake_pyaudio.terminate_count,
            1,
        )

    def test_closed_audio_rejects_operations(
        self,
    ) -> None:
        audio, _ = make_audio()
        audio.close()

        for operation in (
            lambda: audio.say("Hello"),
            lambda: audio.play("sound.wav"),
            lambda: audio.play_note("A4", 0.1),
            lambda: audio.play_melody([]),
            audio.stop,
            audio.is_playing,
        ):
            with (
                self.subTest(operation=operation),
                self.assertRaisesRegex(
                    AudioError,
                    "audio subsystem is closed",
                ),
            ):
                operation()

    def test_context_manager_returns_self_and_closes(
        self,
    ) -> None:
        audio, _ = make_audio()

        with audio as entered:
            self.assertIs(
                entered,
                audio,
            )
            self.assertFalse(audio.closed)

        self.assertTrue(audio.closed)

    def test_playback_session_updates_state_and_amplifier(
        self,
    ) -> None:
        audio, _ = make_audio(
            auto_amp=True,
        )

        with (
            patch(
                "betabox_robotics.audio.audio.enable_speaker",
            ) as enable,
            patch(
                "betabox_robotics.audio.audio.disable_speaker",
            ) as disable,
            audio._playback_session(),
        ):
            self.assertTrue(audio._playing)

        self.assertFalse(audio._playing)
        enable.assert_called_once_with()
        disable.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
