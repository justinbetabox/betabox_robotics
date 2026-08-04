from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
import wave
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Self

import pyaudio

from betabox_robotics.audio.amplifier import (
    disable_speaker,
    enable_speaker,
)
from betabox_robotics.audio.exceptions import (
    AmplifierError,
    AudioError,
    PlaybackError,
)
from betabox_robotics.audio.pronunciation import prepare_speech_text
from betabox_robotics.audio.quiet import suppress_stderr
from betabox_robotics.audio.speech import (
    SpeechBackend,
    available_backends,
    create_backend,
)
from betabox_robotics.audio.tones import (
    MelodyNote,
    NoteValue,
    generate_silence,
    generate_tone,
    note_frequency,
)

if TYPE_CHECKING:
    from betabox_robotics.robots.config import AudioConfig


DEFAULT_OUTPUT_DEVICE: Final[str] = "snd_rpi_hifiberry_dac"
DEFAULT_SAMPLE_RATE: Final[int] = 44_100
DEFAULT_SPEECH_VOLUME: Final[float] = 1.0
MAX_PLAYBACK_VOLUME: Final[float] = 3.0
PLAYBACK_CHUNK_FRAMES: Final[int] = 2_048
AUDIO_CONVERSION_TIMEOUT_SECONDS: Final[float] = 30.0
SPEECH_POSTPROCESS_TIMEOUT_SECONDS: Final[float] = 30.0


@dataclass(
    frozen=True,
    slots=True,
)
class AudioStatus:
    backend: str
    available_backends: list[str]
    output_device_index: int | None
    sample_rate: int
    auto_amp: bool
    keep_amp_enabled: bool
    playing: bool
    closed: bool

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(self)


def _require_nonempty_string(
    value: object,
    *,
    name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(f"{name} must be a string")

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{name} cannot be empty")

    return normalized


def _require_positive_integer(
    value: object,
    *,
    name: str,
) -> int:
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError(f"{name} must be an integer")

    if value <= 0:
        raise ValueError(f"{name} must be greater than 0")

    return value


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


def _require_volume(
    value: object,
    *,
    name: str,
) -> float:
    volume = _require_finite_number(
        value,
        name=name,
    )

    if not 0.0 <= volume <= MAX_PLAYBACK_VOLUME:
        raise ValueError(f"{name} must be between 0.0 and {MAX_PLAYBACK_VOLUME:.1f}")

    return volume


def _unlink_quietly(
    path: Path,
) -> None:
    try:
        path.unlink()
    except OSError:
        pass


class Audio:
    """
    Audio subsystem.

    Provides speech output, sound playback, tone playback, and stop controls.
    """

    def __init__(
        self,
        *,
        speech_backend: SpeechBackend | None = None,
        speech_engine: str = "auto",
        speech_language: str = "en-US",
        piper_model: str | Path | None = None,
        piper_voice: str = "en_US-amy-low",
        preferred_output_device: str = DEFAULT_OUTPUT_DEVICE,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        auto_amp: bool = True,
        keep_amp_enabled: bool = False,
        speech_volume: float = DEFAULT_SPEECH_VOLUME,
    ) -> None:
        if not isinstance(
            auto_amp,
            bool,
        ):
            raise TypeError("auto_amp must be a boolean")

        if not isinstance(
            keep_amp_enabled,
            bool,
        ):
            raise TypeError("keep_amp_enabled must be a boolean")

        if not isinstance(
            preferred_output_device,
            str,
        ):
            raise TypeError("preferred_output_device must be a string")

        output_device = preferred_output_device.strip()

        self.sample_rate = _require_positive_integer(
            sample_rate,
            name="sample_rate",
        )
        self.speech_volume = _require_volume(
            speech_volume,
            name="speech_volume",
        )
        self.auto_amp = auto_amp
        self.keep_amp_enabled = keep_amp_enabled
        self.preferred_output_device = os.getenv(
            "BETABOX_AUDIO_DEVICE",
            output_device,
        ).strip()

        self.speech_backend = speech_backend or create_backend(
            speech_engine=speech_engine,
            speech_language=speech_language,
            piper_model=piper_model,
            piper_voice=piper_voice,
        )

        self._closed = False
        self._playing = False

        try:
            with suppress_stderr():
                self._pyaudio = pyaudio.PyAudio()

        except (
            OSError,
            RuntimeError,
        ) as exc:
            raise PlaybackError(f"failed to initialize audio output: {exc}") from exc

        try:
            self._device_index = self._find_device()

            if self.keep_amp_enabled:
                enable_speaker()

        except (
            AmplifierError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ):
            try:
                self._pyaudio.terminate()
            except (
                OSError,
                RuntimeError,
            ):
                pass

            self._closed = True
            raise

    @classmethod
    def default(
        cls,
        config: AudioConfig,
    ) -> Self:
        return cls(
            speech_engine=config.speech_engine,
            speech_language=config.speech_language,
            piper_model=config.piper_model,
            piper_voice=config.piper_voice,
            preferred_output_device=config.preferred_output_device,
            sample_rate=config.sample_rate,
            auto_amp=config.auto_amp,
            keep_amp_enabled=config.keep_amp_enabled,
            speech_volume=config.speech_volume,
        )

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def speech_backend_name(self) -> str:
        return getattr(
            self.speech_backend,
            "name",
            type(self.speech_backend).__name__,
        )

    def available_speech_backends(
        self,
    ) -> list[str]:
        return available_backends()

    def say(
        self,
        text: str,
    ) -> None:
        self._require_open()

        speech_text = _require_nonempty_string(
            text,
            name="text",
        )

        fd, temporary_name = tempfile.mkstemp(
            prefix="betabox_tts_",
            suffix=".wav",
        )
        os.close(fd)

        synthesized_path = Path(temporary_name)
        processed_path = synthesized_path

        try:
            self.speech_backend.synthesize(
                prepare_speech_text(speech_text),
                synthesized_path,
            )

            processed_path = self._postprocess_speech(
                synthesized_path,
            )

            self.play_wav(processed_path)

        finally:
            if processed_path != synthesized_path:
                _unlink_quietly(processed_path)

            _unlink_quietly(synthesized_path)

    def play(
        self,
        sound: str | Path,
    ) -> None:
        self.play_sound(sound)

    def play_sound(
        self,
        sound: str | Path,
    ) -> None:
        self._require_open()

        path = self._resolve_sound_path(sound)
        wav_path, temporary = self._to_pcm16_wav(path)

        try:
            self.play_wav(wav_path)

        finally:
            if temporary:
                _unlink_quietly(wav_path)

    def play_wav(
        self,
        sound: str | Path,
        *,
        volume: float = 1.0,
    ) -> None:
        self._require_open()

        path = self._require_existing_file(
            sound,
            name="sound",
        )

        playback_volume = _require_volume(
            volume,
            name="volume",
        )

        try:
            with wave.open(
                str(path),
                "rb",
            ) as wav:
                sample_width = wav.getsampwidth()
                compression = wav.getcomptype()
                channels = wav.getnchannels()
                sample_rate = wav.getframerate()

                if sample_width != 2 or compression != "NONE":
                    raise PlaybackError(
                        "only uncompressed 16-bit PCM WAV files are supported"
                    )

                with (
                    self._playback_session(),
                    self._output_stream(
                        channels=channels,
                        sample_rate=sample_rate,
                    ) as stream,
                ):
                    while True:
                        data = wav.readframes(PLAYBACK_CHUNK_FRAMES)

                        if not data:
                            break

                        if playback_volume != 1.0:
                            data = self._scale_pcm16(
                                data,
                                playback_volume,
                            )

                        self._write_stream(
                            stream,
                            data,
                        )

        except PlaybackError:
            raise

        except (
            EOFError,
            OSError,
            wave.Error,
        ) as exc:
            raise PlaybackError(f"failed to play WAV file {path}: {exc}") from exc

    def play_note(
        self,
        note_or_frequency: NoteValue,
        duration: float,
    ) -> None:
        self._require_open()

        duration_value = _require_finite_number(
            duration,
            name="duration",
        )

        if duration_value <= 0:
            raise ValueError("duration must be greater than 0")

        frequency = note_frequency(note_or_frequency)

        data = generate_tone(
            frequency,
            duration_value,
            sample_rate=self.sample_rate,
        )

        self._play_pcm(
            data,
            channels=1,
            sample_rate=self.sample_rate,
        )

    def play_melody(
        self,
        notes: list[MelodyNote],
        *,
        gap: float = 0.0,
    ) -> None:
        self._require_open()

        if not isinstance(
            notes,
            list,
        ):
            raise TypeError("notes must be a list")

        gap_value = _require_finite_number(
            gap,
            name="gap",
        )

        if gap_value < 0:
            raise ValueError("gap cannot be negative")

        prepared_notes: list[bytes] = []

        for note_or_frequency, duration in notes:
            duration_value = _require_finite_number(
                duration,
                name="duration",
            )

            if duration_value <= 0:
                raise ValueError("melody note duration must be greater than 0")

            frequency = note_frequency(note_or_frequency)

            tone = generate_tone(
                frequency,
                duration_value,
                sample_rate=self.sample_rate,
            )

            prepared_notes.append(tone)

        if not prepared_notes:
            return

        silence = (
            generate_silence(
                gap_value,
                sample_rate=self.sample_rate,
            )
            if gap_value > 0
            else b""
        )

        with (
            self._playback_session(),
            self._output_stream(
                channels=1,
                sample_rate=self.sample_rate,
            ) as stream,
        ):
            for data in prepared_notes:
                self._write_stream(
                    stream,
                    data,
                )

                if silence:
                    self._write_stream(
                        stream,
                        silence,
                    )

    def stop(self) -> None:
        """
        Disable the speaker amplifier.

        Playback is synchronous, so this cannot interrupt a playback call
        running in the same thread. The method remains part of the public API
        for amplifier shutdown and future interruptible playback support.
        """
        self._require_open()

        if self.auto_amp and not self.keep_amp_enabled:
            disable_speaker()

    def is_playing(self) -> bool:
        self._require_open()
        return self._playing

    def status(self) -> AudioStatus:
        return AudioStatus(
            backend=self.speech_backend_name,
            available_backends=(self.available_speech_backends()),
            output_device_index=self._device_index,
            sample_rate=self.sample_rate,
            auto_amp=self.auto_amp,
            keep_amp_enabled=self.keep_amp_enabled,
            playing=self._playing,
            closed=self.closed,
        )

    def close(self) -> None:
        if self._closed:
            return

        first_error: AmplifierError | OSError | RuntimeError | None = None

        try:
            if self.auto_amp or self.keep_amp_enabled:
                try:
                    disable_speaker()

                except (
                    AmplifierError,
                    OSError,
                    RuntimeError,
                ) as exc:
                    first_error = exc

            try:
                self._pyaudio.terminate()

            except (
                OSError,
                RuntimeError,
            ) as exc:
                if first_error is None:
                    first_error = exc

        finally:
            self._closed = True
            self._playing = False

        if first_error is not None:
            raise first_error

    def deinit(self) -> None:
        self.close()

    def _require_open(self) -> None:
        if self._closed:
            raise AudioError("audio subsystem is closed")

    @staticmethod
    def _require_existing_file(
        value: str | Path,
        *,
        name: str,
    ) -> Path:
        if isinstance(value, bool) or not isinstance(
            value,
            str | Path,
        ):
            raise TypeError(f"{name} must be a string or Path")

        path = Path(value).expanduser()

        if not path.is_file():
            raise PlaybackError(f"sound file does not exist: {path}")

        return path

    def _find_device(self) -> int | None:
        requested_name = self.preferred_output_device.lower()

        try:
            device_count = self._pyaudio.get_device_count()

        except (
            OSError,
            RuntimeError,
        ):
            device_count = 0

        for index in range(device_count):
            try:
                info = self._pyaudio.get_device_info_by_index(index)

            except (
                OSError,
                RuntimeError,
            ):
                continue

            try:
                name = str(
                    info.get(
                        "name",
                        "",
                    )
                ).lower()

                output_channels = int(
                    info.get(
                        "maxOutputChannels",
                        0,
                    )
                    or 0
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

            if requested_name and requested_name in name and output_channels > 0:
                return index

        try:
            info = self._pyaudio.get_default_output_device_info()

            return int(info["index"])

        except (
            KeyError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ):
            return None

    def _resolve_sound_path(
        self,
        sound: str | Path,
    ) -> Path:
        if isinstance(sound, bool) or not isinstance(
            sound,
            str | Path,
        ):
            raise TypeError("sound must be a string or Path")

        raw_path = Path(sound).expanduser()
        candidate_names = [raw_path]

        if not raw_path.suffix:
            candidate_names.extend(
                Path(f"{raw_path}{suffix}")
                for suffix in (
                    ".wav",
                    ".mp3",
                    ".ogg",
                    ".m4a",
                    ".flac",
                )
            )

        if raw_path.is_absolute():
            for candidate in candidate_names:
                if candidate.is_file():
                    return candidate

            raise PlaybackError(f"sound file does not exist: {sound}")

        for candidate in candidate_names:
            if candidate.is_file():
                return candidate

        search_directories = (
            Path.cwd(),
            Path.home() / "media" / "sounds",
            (Path(__file__).resolve().parent / "sounds"),
        )

        for directory in search_directories:
            for candidate in candidate_names:
                path = directory / candidate.name

                if path.is_file():
                    return path

        raise PlaybackError(f"sound file does not exist: {sound}")

    def _to_pcm16_wav(
        self,
        path: Path,
    ) -> tuple[Path, bool]:
        try:
            with wave.open(
                str(path),
                "rb",
            ) as wav:
                if wav.getsampwidth() == 2 and wav.getcomptype() == "NONE":
                    return path, False

        except (
            EOFError,
            OSError,
            wave.Error,
        ):
            pass

        fd, temporary_name = tempfile.mkstemp(
            prefix="betabox_audio_",
            suffix=".wav",
        )
        os.close(fd)

        output_path = Path(temporary_name)

        try:
            command = self._audio_conversion_command(
                source_path=path,
                output_path=output_path,
            )

            self._run_audio_command(
                command,
                operation="audio conversion",
                timeout=(AUDIO_CONVERSION_TIMEOUT_SECONDS),
            )

        except PlaybackError:
            _unlink_quietly(output_path)
            raise

        return output_path, True

    def _audio_conversion_command(
        self,
        *,
        source_path: Path,
        output_path: Path,
    ) -> list[str]:
        ffmpeg = shutil.which("ffmpeg")

        if ffmpeg is not None:
            return [
                ffmpeg,
                "-y",
                "-i",
                str(source_path),
                "-ac",
                "1",
                "-ar",
                str(self.sample_rate),
                "-c:a",
                "pcm_s16le",
                str(output_path),
            ]

        sox = shutil.which("sox")

        if sox is not None:
            return [
                sox,
                str(source_path),
                "-b",
                "16",
                "-c",
                "1",
                "-r",
                str(self.sample_rate),
                str(output_path),
            ]

        raise PlaybackError(
            "install ffmpeg or sox to play compressed or non-WAV audio files"
        )

    @staticmethod
    def _run_audio_command(
        command: list[str],
        *,
        operation: str,
        timeout: float,
    ) -> None:
        try:
            subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=timeout,
            )

        except subprocess.TimeoutExpired as exc:
            raise PlaybackError(
                f"{operation} timed out after {timeout:g} seconds"
            ) from exc

        except subprocess.CalledProcessError as exc:
            details = exc.stderr.strip() if exc.stderr else ""

            message = (
                f"{operation} failed: {details}" if details else f"{operation} failed"
            )

            raise PlaybackError(message) from exc

        except OSError as exc:
            raise PlaybackError(f"failed to start {operation}: {exc}") from exc

    def _enable_amp_for_playback(self) -> None:
        if self.auto_amp and not self.keep_amp_enabled:
            enable_speaker()

    def _disable_amp_after_playback(self) -> None:
        if self.auto_amp and not self.keep_amp_enabled:
            disable_speaker()

    @contextmanager
    def _playback_session(
        self,
    ) -> Generator[None, None, None]:
        self._enable_amp_for_playback()
        self._playing = True

        try:
            yield

        finally:
            self._playing = False
            self._disable_amp_after_playback()

    @contextmanager
    def _output_stream(
        self,
        *,
        channels: int,
        sample_rate: int,
    ) -> Generator[Any, None, None]:
        stream_kwargs: dict[str, Any] = {
            "format": pyaudio.paInt16,
            "channels": channels,
            "rate": sample_rate,
            "output": True,
        }

        if self._device_index is not None:
            stream_kwargs["output_device_index"] = self._device_index

        try:
            with suppress_stderr():
                stream = self._pyaudio.open(**stream_kwargs)

        except (
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as exc:
            raise PlaybackError(f"failed to open audio output: {exc}") from exc

        try:
            yield stream

        finally:
            first_error: OSError | RuntimeError | None = None

            try:
                stream.stop_stream()

            except (
                OSError,
                RuntimeError,
            ) as exc:
                first_error = exc

            try:
                stream.close()

            except (
                OSError,
                RuntimeError,
            ) as exc:
                if first_error is None:
                    first_error = exc

            if first_error is not None:
                raise PlaybackError(
                    f"failed to close audio output stream: {first_error}"
                ) from first_error

    @staticmethod
    def _write_stream(
        stream: Any,
        data: bytes,
    ) -> None:
        try:
            stream.write(data)

        except (
            OSError,
            RuntimeError,
        ) as exc:
            raise PlaybackError(f"audio playback failed: {exc}") from exc

    def _play_pcm(
        self,
        data: bytes,
        *,
        channels: int,
        sample_rate: int,
    ) -> None:
        with (
            self._playback_session(),
            self._output_stream(
                channels=channels,
                sample_rate=sample_rate,
            ) as stream,
        ):
            self._write_stream(
                stream,
                data,
            )

    @staticmethod
    def _scale_pcm16(
        data: bytes,
        volume: float,
    ) -> bytes:
        if volume == 1.0:
            return data

        output = bytearray(len(data))

        for index in range(
            0,
            len(data),
            2,
        ):
            sample = int.from_bytes(
                data[index : index + 2],
                "little",
                signed=True,
            )

            scaled_sample = int(sample * volume)

            clamped_sample = max(
                -32_768,
                min(
                    32_767,
                    scaled_sample,
                ),
            )

            output[index : index + 2] = clamped_sample.to_bytes(
                2,
                "little",
                signed=True,
            )

        return bytes(output)

    def _postprocess_speech(
        self,
        wav_path: Path,
    ) -> Path:
        if self.speech_volume == 1.0:
            return wav_path

        return self._apply_wav_volume(
            wav_path,
            self.speech_volume,
        )

    def _apply_wav_volume(
        self,
        wav_path: Path,
        volume: float,
    ) -> Path:
        ffmpeg = shutil.which("ffmpeg")

        if ffmpeg is None:
            return wav_path

        fd, temporary_name = tempfile.mkstemp(
            prefix="betabox_speech_",
            suffix=".wav",
        )
        os.close(fd)

        output_path = Path(temporary_name)

        try:
            self._run_audio_command(
                [
                    ffmpeg,
                    "-y",
                    "-i",
                    str(wav_path),
                    "-filter:a",
                    f"volume={volume}",
                    "-c:a",
                    "pcm_s16le",
                    str(output_path),
                ],
                operation="speech volume processing",
                timeout=(SPEECH_POSTPROCESS_TIMEOUT_SECONDS),
            )

        except PlaybackError:
            _unlink_quietly(output_path)
            raise

        return output_path

    def __enter__(self) -> Self:
        self._require_open()
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()
