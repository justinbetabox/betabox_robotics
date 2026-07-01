# Betabox Audio Architecture

**Status:** Foundation  
**Project:** Betabox Robot Platform

---

# Purpose

The Audio subsystem provides speech output, sound playback, tone generation,
and melody playback for the Betabox Robot Platform.

It presents a simple, platform-independent API while hiding the underlying
details of audio devices, amplifier control, speech engines, file conversion,
and playback implementation.

The goal is to provide a consistent audio experience across all Betabox robots
without exposing Linux-specific implementation details to applications.

---

# Responsibilities

The Audio subsystem is responsible for:

- Speech synthesis
- Sound playback
- Tone generation
- Melody playback
- Speaker amplifier management
- Audio device selection
- Speech backend selection
- Speech pronunciation preprocessing
- Speech post-processing
- Audio format conversion

---

# Public API

```python
from betabox_car.audio import Audio

with Audio() as audio:
    audio.say("Hello from Betabox")

    audio.play_sound("car-honk")

    audio.play_note("C5", 0.5)

    audio.play_melody(
        [
            ("C5", 0.2),
            ("D5", 0.2),
            ("E5", 0.2),
            ("G5", 0.4),
        ],
        gap=0.05,
    )

    audio.stop()
```

`play()` is provided as a convenience alias:

```python
audio.play("car-honk")
```

---

# Speech

Speech output is implemented using pluggable speech backends.

Supported speech engines include:

- pico2wave
- espeak-ng
- Piper

The default automatic backend selection is:

```
pico2wave
    ↓
espeak-ng
```

Piper is supported as an optional high-quality speech backend.

Example:

```python
audio = Audio(
    speech_engine="piper",
    piper_voice="en_US-amy-low",
)

audio.say("Hello from Betabox")
```

---

# Speech Pronunciation

Before speech synthesis, text is passed through a pronunciation preprocessing
stage.

This allows project-specific words to be spoken consistently across every
speech backend.

Applications should write natural text:

```python
audio.say("Hello from Betabox")
```

The Audio subsystem internally applies pronunciation replacements where
necessary.

---

# Speech Volume

Speech output may be amplified during post-processing.

```python
audio = Audio(
    speech_volume=1.8,
)
```

Speech post-processing exists independently of playback so that only synthesized
speech is modified.

This avoids unintentionally changing the loudness of sound effects or generated
tones.

---

# Sound Playback

Sound playback uses the same playback pipeline as speech.

The preferred audio format is:

```
16-bit PCM WAV
44.1 kHz
```

When available, FFmpeg or SoX may automatically convert common audio formats
including:

- MP3
- OGG
- FLAC
- M4A
- AAC

Using native WAV files provides the fastest playback and avoids conversion
overhead.

---

# Sound Lookup

When a filename is supplied, Audio searches multiple locations.

Search order:

1. Explicit file path
2. Current working directory
3. `~/media/sounds`
4. Built-in Betabox sounds

Example:

```python
audio.play_sound("car-honk")
```

This allows applications to use either project-specific assets or shared
Betabox sounds.

---

# Tone Generation

Single tones may be generated using note names or frequencies.

Examples:

```python
audio.play_note("C5", 0.5)

audio.play_note("A4", 0.25)

audio.play_note(440.0, 0.5)
```

Supported note names include:

```
C
C#
Db
D
D#
Eb
E
F
F#
Gb
G
G#
Ab
A
A#
Bb
B
```

---

# Melody Playback

Sequences of notes can be played using `play_melody()`.

Example:

```python
audio.play_melody(
    [
        ("C5", 0.25),
        ("D5", 0.25),
        ("E5", 0.25),
        ("G5", 0.5),
    ],
    gap=0.05,
)
```

Melodies are played synchronously.

---

# Speaker Amplifier

Betabox robots include a software-controlled speaker amplifier.

By default, the amplifier is enabled only while audio is playing.

For applications that play many sounds in succession, amplifier switching may
be disabled:

```python
with Audio(
    keep_amp_enabled=True,
) as audio:
    ...
```

This reduces repeated amplifier toggling during continuous playback.

---

# Diagnostics

Applications can inspect the currently selected speech backend.

```python
audio.speech_backend_name
```

Example:

```
pico2wave
```

Available speech engines can also be queried.

```python
audio.available_speech_backends()
```

Example:

```python
["pico2wave", "espeak-ng", "piper"]
```

---

# Design Principles

The Audio subsystem intentionally hides implementation details.

Applications should not directly depend upon:

- PyAudio
- ALSA
- pico2wave
- espeak-ng
- Piper
- FFmpeg
- SoX
- amplifier GPIO control
- Linux audio device names

These remain internal implementation details that may evolve over time.

The public API is designed to remain stable even if the underlying
implementation changes.

---

# Future Expansion

Potential future capabilities include:

- Asynchronous playback
- Pause and resume
- Speech caching
- Audio playlists
- Built-in sound libraries
- Configurable audio profiles
- Microphone support
- Audio recording
- Voice activity detection
- Streaming audio

These additions should extend the existing API without requiring changes to
student applications.
