import os
import shutil
import subprocess
import tempfile
import wave
from contextlib import contextmanager
from pathlib import Path
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pyaudio

from betabox_robotics.audio.amplifier import disable_speaker, enable_speaker
from betabox_robotics.audio.exceptions import AudioError
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

@dataclass(frozen=True)
class AudioStatus:
    backend: str
    available_backends: list[str]
    output_device_index: int | None
    sample_rate: int
    auto_amp: bool
    keep_amp_enabled: bool
    playing: bool
    closed: bool


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
        preferred_output_device: str = "snd_rpi_hifiberry_dac",
        sample_rate: int = 44100,
        auto_amp: bool = True,
        keep_amp_enabled: bool = False,
        speech_volume: float = 1.0,
    ) -> None:
        self.speech_backend = speech_backend or create_backend(
            speech_engine=speech_engine,
            speech_language=speech_language,
            piper_model=piper_model,
            piper_voice=piper_voice,
        )

        self.preferred_output_device = os.getenv(
            "BETABOX_AUDIO_DEVICE", preferred_output_device
        )
        self.sample_rate = int(sample_rate)
        self.auto_amp = auto_amp
        self.keep_amp_enabled = keep_amp_enabled
        self.speech_volume = float(speech_volume)

        with suppress_stderr():
            self._pyaudio = pyaudio.PyAudio()
        self._device_index = self._find_device()
        if self.keep_amp_enabled:
            enable_speaker()

        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def _require_open(self) -> None:
        if self._closed:
            raise AudioError("audio subsystem is closed")

    @classmethod
    def default(
        cls,
        config: "AudioConfig",
    ) -> "Audio":
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

    def say(self, text: str) -> None:
        self._require_open()

        if not text:
            raise AudioError("speech text cannot be empty")

        fd, wav_path = tempfile.mkstemp(prefix="betabox_tts_", suffix=".wav")
        os.close(fd)

        try:
            spoken_text = prepare_speech_text(text)
            self.speech_backend.synthesize(spoken_text, wav_path)
            processed_path = self._postprocess_speech(Path(wav_path))

            try:
                self.play_wav(processed_path)
            finally:
                if processed_path != Path(wav_path):
                    try:
                        processed_path.unlink()
                    except OSError:
                        pass
        finally:
            try:
                os.remove(wav_path)
            except OSError:
                pass

    def play(self, sound: str | Path) -> None:
        self._require_open()

        self.play_sound(sound)

    def play_sound(self, sound: str | Path) -> None:
        self._require_open()

        path = self._resolve_sound_path(sound)
        wav_path, is_temp = self._to_pcm16_wav(path)

        try:
            self.play_wav(wav_path)
        finally:
            if is_temp:
                try:
                    wav_path.unlink()
                except OSError:
                    pass

    def play_wav(self, sound: str | Path, *, volume: float = 1.0) -> None:
        self._require_open()

        path = Path(sound)

        if not path.exists():
            raise AudioError(f"sound file does not exist: {path}")

        with wave.open(str(path), "rb") as wav:
            sample_width = wav.getsampwidth()
            channels = wav.getnchannels()
            rate = wav.getframerate()

            if sample_width != 2:
                raise AudioError(
                    f"only 16-bit PCM WAV files are supported; got sample_width={sample_width}"
                )

            with self._playback_session():
                with self._output_stream(
                    channels=channels,
                    sample_rate=rate,
                ) as stream:
                    while True:
                        data = wav.readframes(2048)

                        if not data:
                            break

                        if volume != 1.0:
                            data = self._scale_pcm16(data, volume)
                        stream.write(data)

    def play_note(
        self,
        note_or_frequency: NoteValue,
        duration: float,
    ) -> None:
        self._require_open()

        if duration <= 0:
            raise AudioError("note duration must be greater than 0")

        frequency = note_frequency(note_or_frequency)

        if frequency <= 0:
            raise AudioError("frequency must be greater than 0")

        data = generate_tone(
            frequency,
            duration,
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

        if gap < 0:
            raise AudioError("melody gap cannot be negative")

        for note_or_frequency, duration in notes:
            if duration <= 0:
                raise AudioError("melody note duration must be greater than 0")

        if not notes:
            return

        with self._playback_session():
            with self._output_stream(
                channels=1,
                sample_rate=self.sample_rate,
            ) as stream:
                for note_or_frequency, duration in notes:
                    frequency = note_frequency(note_or_frequency)

                    data = generate_tone(
                        frequency,
                        duration,
                        sample_rate=self.sample_rate,
                    )

                    stream.write(data)

                    if gap > 0:
                        silence = generate_silence(
                            gap,
                            sample_rate=self.sample_rate,
                        )
                        stream.write(silence)

    def stop(self) -> None:
        """
        Disable the speaker amplifier.

        Playback is currently synchronous, so this method cannot interrupt
        an active playback operation. It is reserved for future asynchronous
        playback support.
        """
        self._require_open()

        if self.auto_amp and not self.keep_amp_enabled:
            disable_speaker()

    def is_playing(self) -> bool:
        """
        Return whether asynchronous playback is active.

        Playback is currently synchronous, so this always returns False.
        """
        self._require_open()
        return False

    @property
    def speech_backend_name(self) -> str:
        return getattr(
            self.speech_backend,
            "name",
            type(self.speech_backend).__name__,
        )

    def available_speech_backends(self) -> list[str]:
        return available_backends()

    def close(self) -> None:
        if self._closed:
            return

        try:
            self.stop()

            if self.keep_amp_enabled:
                disable_speaker()
        finally:
            self._pyaudio.terminate()
            self._closed = True

    def deinit(self) -> None:
        self.close()

    def _find_device(self) -> int | None:
        device_name = (self.preferred_output_device or "").lower()

        for index in range(self._pyaudio.get_device_count()):
            info = self._pyaudio.get_device_info_by_index(index)
            name = str(info.get("name", "")).lower()

            if device_name and device_name in name:
                return index

        try:
            return int(self._pyaudio.get_default_output_device_info()["index"])
        except Exception:
            return None

    def _resolve_sound_path(self, sound: str | Path) -> Path:
        raw_path = Path(sound).expanduser()

        search_dirs = [
            Path.cwd(),
            Path.home() / "media" / "sounds",
            Path(__file__).resolve().parent / "sounds",
        ]

        candidate_names = [raw_path]

        if raw_path.suffix == "":
            candidate_names.extend(
                [
                    Path(f"{raw_path}.wav"),
                    Path(f"{raw_path}.mp3"),
                    Path(f"{raw_path}.ogg"),
                    Path(f"{raw_path}.m4a"),
                    Path(f"{raw_path}.flac"),
                ]
            )

        if raw_path.is_absolute():
            for candidate in candidate_names:
                if candidate.exists():
                    return candidate

            raise AudioError(f"sound file does not exist: {sound}")

        for candidate in candidate_names:
            if candidate.exists():
                return candidate

        for directory in search_dirs:
            for candidate in candidate_names:
                path = directory / candidate.name

                if path.exists():
                    return path

        raise AudioError(f"sound file does not exist: {sound}")

    def _to_pcm16_wav(self, path: Path) -> tuple[Path, bool]:
        try:
            with wave.open(str(path), "rb") as wav:
                if wav.getsampwidth() == 2 and wav.getcomptype() == "NONE":
                    return path, False
        except wave.Error:
            pass

        fd, temp_path = tempfile.mkstemp(prefix="betabox_audio_", suffix=".wav")
        os.close(fd)

        temp = Path(temp_path)

        ffmpeg = shutil.which("ffmpeg")
        sox = shutil.which("sox")

        if ffmpeg:
            command = [
                ffmpeg,
                "-y",
                "-i",
                str(path),
                "-ac",
                "1",
                "-ar",
                "44100",
                "-sample_fmt",
                "s16",
                str(temp),
            ]
        elif sox:
            command = [
                sox,
                str(path),
                "-b",
                "16",
                "-c",
                "1",
                "-r",
                "44100",
                str(temp),
            ]
        else:
            raise AudioError("install ffmpeg or sox to play non-WAV audio files")

        try:
            subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            try:
                temp.unlink()
            except OSError:
                pass

            raise AudioError(f"audio conversion failed: {exc.stderr}") from exc

        return temp, True

    def _enable_amp_for_playback(self) -> None:
        if self.auto_amp and not self.keep_amp_enabled:
            enable_speaker()

    def _disable_amp_after_playback(self) -> None:
        if self.auto_amp and not self.keep_amp_enabled:
            disable_speaker()

    @contextmanager
    def _playback_session(self):
        self._enable_amp_for_playback()

        try:
            yield
        finally:
            self._disable_amp_after_playback()

    @contextmanager
    def _output_stream(
        self,
        *,
        channels: int,
        sample_rate: int,
    ):
        stream_kwargs = {
            "format": pyaudio.paInt16,
            "channels": channels,
            "rate": sample_rate,
            "output": True,
        }

        if self._device_index is not None:
            stream_kwargs["output_device_index"] = self._device_index

        with suppress_stderr():
            stream = self._pyaudio.open(**stream_kwargs)

        try:
            yield stream
        finally:
            stream.stop_stream()
            stream.close()

    def _play_pcm(
        self,
        data: bytes,
        *,
        channels: int,
        sample_rate: int,
    ) -> None:
        with self._playback_session():
            with self._output_stream(
                channels=channels,
                sample_rate=sample_rate,
            ) as stream:
                stream.write(data)

    def _scale_pcm16(self, data: bytes, volume: float) -> bytes:
        scale = max(0.0, min(3.0, float(volume)))

        if scale == 1.0:
            return data

        output = bytearray(len(data))

        for index in range(0, len(data), 2):
            sample = int.from_bytes(data[index : index + 2], "little", signed=True)
            sample = int(sample * scale)
            sample = max(-32768, min(32767, sample))
            output[index : index + 2] = sample.to_bytes(2, "little", signed=True)

        return bytes(output)

    def _postprocess_speech(
        self,
        wav_path: Path,
    ) -> Path:
        if self.speech_volume == 1.0:
            return wav_path

        return self._apply_wav_volume(wav_path, self.speech_volume)

    def _apply_wav_volume(
        self,
        wav_path: Path,
        volume: float,
    ) -> Path:
        scale = max(0.0, min(3.0, float(volume)))

        ffmpeg = shutil.which("ffmpeg")

        if ffmpeg is None:
            return wav_path

        fd, temp_path = tempfile.mkstemp(
            prefix="betabox_speech_",
            suffix=".wav",
        )
        os.close(fd)

        output_path = Path(temp_path)

        command = [
            ffmpeg,
            "-y",
            "-i",
            str(wav_path),
            "-filter:a",
            f"volume={scale}",
            str(output_path),
        ]

        try:
            subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            try:
                output_path.unlink()
            except OSError:
                pass

            raise AudioError(
                f"speech volume processing failed: {exc.stderr}"
            ) from exc

        return output_path

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def status(self) -> AudioStatus:
        return AudioStatus(
            backend=self.speech_backend_name,
            available_backends=available_backends(),
            output_device_index=self._device_index,
            sample_rate=self.sample_rate,
            auto_amp=self.auto_amp,
            keep_amp_enabled=self.keep_amp_enabled,
            playing=False,
            closed=self.closed,
        )
