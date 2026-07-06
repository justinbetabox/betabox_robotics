# Betabox Audio Architecture

**Status:** Foundation  
**Project:** Betabox Robot Platform

------------------------------------------------------------------------

## Purpose

The Audio subsystem provides speech output, sound playback, tone generation,
and melody playback for the Betabox Robot Platform.

It presents a simple, platform-independent API while hiding the underlying
details of audio devices, amplifier control, speech engines, file conversion,
and playback implementation.

The goal is to provide a consistent audio experience across all Betabox robots
without exposing Linux-specific implementation details to applications.

------------------------------------------------------------------------

## Robot Composition

The Audio subsystem is a reusable subsystem implementation.

Robot implementations provide the configuration required to initialize the
Audio subsystem.

Applications should normally access audio through:

```python
from betabox_robotics import Robot

robot = Robot()

robot.audio.say("Hello from Betabox")
```

rather than constructing `Audio` directly.

Constructing `Audio` directly remains appropriate for testing, validation,
and advanced configuration.

------------------------------------------------------------------------

## Responsibilities

The Audio subsystem is responsible for:

-    Speech synthesis
-    Sound playback
-    Tone generation
-    Melody playback
-    Speaker amplifier management
-    Audio output management
-    Speech backend selection
-    Speech pronunciation preprocessing
-    Speech post-processing
-    Audio format conversion
------------------------------------------------------------------------

## Non-Responsibilities

The Audio subsystem is **not** responsible for:

-    Robot movement
-    Sensor acquisition
-    Vision processing
-    Camera control
-    Platform status
-    User interface behavior

The Audio subsystem produces audio.

Higher-level systems decide **when** audio should be played.

------------------------------------------------------------------------

## Public API

```python
from betabox_robotics import Robot

robot = Robot()

robot.audio.say("Hello from Betabox")

robot.audio.play_sound("car-honk")

robot.audio.play_note("C5", 0.5)

robot.audio.play_melody(
    [
        ("C5", 0.2),
        ("D5", 0.2),
        ("E5", 0.2),
        ("G5", 0.4),
    ],
    gap=0.05,
)

robot.audio.stop()
```

`play()` is provided as a convenience alias:

```python
robot.audio.play("car-honk")
```

------------------------------------------------------------------------

## Speech

Speech output is implemented using pluggable speech backends.

Applications interact with a stable speech API regardless of the selected backend.

Supported speech engines include:

-    pico2wave
-    espeak-ng
-    Piper

The default automatic backend selection is:

```text
pico2wave
    │
    ▼
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

------------------------------------------------------------------------

## Speech Pronunciation

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

------------------------------------------------------------------------

## Speech Volume

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

------------------------------------------------------------------------

## Sound Playback

Sound playback uses the same playback pipeline as speech.

The preferred audio format is:

```text
16-bit PCM WAV
44.1 kHz
```

When available, FFmpeg or SoX may automatically convert common audio formats
including:

-    MP3
-    OGG
-    FLAC
-    M4A
-    AAC

Using native WAV files provides the fastest playback and avoids conversion
overhead.

------------------------------------------------------------------------

## Sound Lookup

When a filename is supplied, Audio searches multiple locations.

Search order:

-    Explicit file path
-    Current working directory
-    `~/media/sounds`
-    Built-in Betabox sounds

Example:

```python
audio.play_sound("car-honk")
```

This allows applications to use either project-specific assets or shared
Betabox sounds.

------------------------------------------------------------------------

## Tone Generation

Single tones may be generated using note names or frequencies.

Examples:

```python
audio.play_note("C5", 0.5)

audio.play_note("A4", 0.25)

audio.play_note(440.0, 0.5)
```

Supported note names include:

```text
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

------------------------------------------------------------------------

## Melody Playback

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

------------------------------------------------------------------------

## Speaker Amplifier

Some Betabox robot platforms include a software-controlled speaker amplifier.

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

------------------------------------------------------------------------

## Resource Ownership

The Audio subsystem owns all resources required for audio playback.

Examples include:

- Audio output device
- Speech backend
- Playback pipeline
- Speaker amplifier (when present)

Other subsystems should not directly control audio hardware.

Robot implementations provide any platform-specific configuration required
to initialize these resources.

------------------------------------------------------------------------

## Interaction with Other Subsystems

Applications request audio through the Robot API.

```text
Applications
     │
     ▼
 Robot API
     │
     ▼
   Audio
     │
     ▼
Audio Hardware
```

The Audio subsystem performs audio playback.

Higher-level systems determine when audio should be produced.

------------------------------------------------------------------------

## Diagnostics

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

------------------------------------------------------------------------

## Implementation Boundaries

The Audio subsystem intentionally hides implementation details.

Applications should not directly depend upon:

-    PyAudio
-    ALSA
-    pico2wave
-    espeak-ng
-    Piper
-    FFmpeg
-    SoX
-    amplifier GPIO control
-    Linux audio device names

These remain internal implementation details that may evolve over time.

The public API is designed to remain stable even if the underlying
implementation changes.

------------------------------------------------------------------------

## Future Expansion

Potential future capabilities include:

-    Asynchronous playback
-    Pause and resume
-    Speech caching
-    Audio playlists
-    Built-in sound libraries
-    Configurable audio profiles
-    Microphone support
-    Audio recording
-    Voice activity detection
-    Streaming audio
-    Robot-specific audio configurations

These additions should extend the existing API without requiring changes to
student applications.

------------------------------------------------------------------------

## Summary

The Audio subsystem provides a stable interface for speech synthesis,
sound playback, and tone generation.

It owns the robot's audio resources while hiding platform-specific
implementation details behind a consistent public API.

Higher-level systems determine when audio should be played.

The Audio subsystem determines how that audio is produced.
