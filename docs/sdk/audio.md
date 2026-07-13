# Betabox Audio Architecture

**Status:** Foundation  
**Project:** Betabox Robot Platform
**Document:** `audio.md`

------------------------------------------------------------------------

## Purpose

The Audio subsystem provides a stable, reusable interface for speech synthesis, sound playback, tone generation, and melody playback.

It presents a simple, hardware-independent API while hiding the details of audio devices, amplifier control, speech engines, file conversion, and operating-system-specific implementation.

Student code should describe what the robot should say or play, not how audio is produced.

------------------------------------------------------------------------

## Robot Composition

The Audio subsystem is a reusable subsystem implementation composed into a robot implementation.

Robot implementations provide the configuration required to construct the Audio subsystem, including audio devices, speech backend preferences, media locations, and platform-specific hardware.

Applications should normally access audio through the Robot API:

```python
from betabox_robotics import BetaboxCar

with BetaboxCar() as car:
    car.say("Hello from Betabox")

    car.play("car-honk")
```

The Audio subsystem remains available when more detailed control is appropriate:

```python
car.audio.say("Hello from Betabox")

car.audio.play("car-honk")

car.audio.play_note("C5", 0.5)
```

Constructing the Audio subsystem directly is generally reserved for hardware validation, subsystem validation, testing, and advanced applications.

------------------------------------------------------------------------

## Responsibilities

The Audio subsystem is responsible for:

### Speech

-    Speech synthesis
-    Speech backend selection
-    Consistent speech output

### Playback

-    Sound playback
-    Tone generation
-    Melody playback
-    Audio output management

### Resource Ownership

-    Manage audio hardware
-    Coordinate playback resources
-    Control platform-specific amplifier hardware when required

### Configuration

-    Apply robot-specific audio configuration
-    Locate media assets
-    Configure speech backends
-    Apply playback settings
 
------------------------------------------------------------------------

## Non-Responsibilities

The Audio subsystem is not responsible for:

-    Robot movement
-    Sensor acquisition
-    Vision processing
-    Camera control
-    Platform status
-    User interface behavior

The Audio subsystem produces audio.

Higher-level software decides when audio should be played.

------------------------------------------------------------------------

## Public API

### Robot API

The Robot API provides convenient audio methods intended for most applications.

```python
car.say(text)

car.play(sound)

car.play_note(note_or_frequency, duration)

car.play_melody(notes, gap=0.0)

car.stop_audio()

car.is_audio_playing()
```

### Audio Subsystem API

The reusable Audio subsystem remains available for applications requiring more detailed control.

```python
car.audio.say(text)

car.audio.play(sound)

car.audio.play_note(note_or_frequency, duration)

car.audio.play_melody(notes, gap=0.0)

car.audio.stop()

car.audio.is_playing()
```

------------------------------------------------------------------------

## Speech

Applications interact with a stable speech interface regardless of the selected speech engine.

Robot implementations may configure one or more supported speech backends.

Examples include:

-    pico2wave
-    espeak-ng
-    Piper

The Audio subsystem automatically selects an appropriate configured backend.

Applications should simply write natural text:

car.say("Hello from Betabox")

Pronunciation adjustments and backend-specific behavior remain internal implementation details.

------------------------------------------------------------------------

## Sound Playback

The Audio subsystem provides consistent sound playback regardless of file format or playback implementation.

Preferred sound assets use native WAV files.

When supported, common formats may be converted automatically.

Applications simply request a sound by name or filename:

```python
car.play("car-honk")
```

Robot implementations may configure additional media search locations when appropriate.

------------------------------------------------------------------------

## Speech Volume

Single tones may be generated using either musical note names or frequencies.

Examples:

```python
car.play_note("C5", 0.5)

car.play_note("A4", 0.25)

car.play_note(440.0, 0.5)
```

------------------------------------------------------------------------

## Melody Playback

Sequences of notes may be played using play_melody().

Example:

```python
car.play_melody(
    [
        ("C5", 0.25),
        ("D5", 0.25),
        ("E5", 0.25),
        ("G5", 0.5),
    ],
    gap=0.05,
)
```

Melodies are played synchronously unless a future asynchronous playback mode is explicitly requested.

------------------------------------------------------------------------

## Resource Ownership

The Audio subsystem owns all resources required for audio playback.

Examples include:

-    Audio output device
-    Playback pipeline
-    Speech backend
-    Speaker amplifier (when present)

Applications and other subsystems should not directly control these resources.

Robot implementations supply any platform-specific configuration required to initialize them.

------------------------------------------------------------------------

## Behavior Guarantees

The Audio subsystem should provide predictable behavior.

Expected guarantees include:

-    Playback requests use the configured audio pipeline.
-    Speech behaves consistently regardless of backend.
-    Platform-specific hardware is managed automatically.
-    Playback resources are released during cleanup.
-    Internal implementation details remain hidden from applications.

------------------------------------------------------------------------

## Interaction with Other Subsystems

Applications request audio through the Robot API.

```text
 Robot API
     │
     ▼
   Audio
     │
     ▼
Audio Hardware
```

Examples:

```text
  Vision
    │
    ▼
  Audio

  System
    │
    ▼
  Audio

Curriculum
    │
    ▼
  Audio
```

The Audio subsystem produces audio.

Other subsystems determine when playback should occur.

------------------------------------------------------------------------

## Implementation Details

Implementation details intentionally remain hidden.

Applications should not depend directly on:

-    Linux audio devices
-    ALSA
-    Speech engines
-    FFmpeg
-    SoX
-    GPIO amplifier control
-    Platform-specific playback libraries

These implementation details may evolve while the public API remains stable.

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
-    Robot-specific audio configuration

Future capabilities should extend the existing API without requiring changes to student applications.

------------------------------------------------------------------------

## Testing and Validation

The Audio subsystem should be verified through multiple forms of testing.

These include:

-    Unit tests
-    Hardware validation
-    Subsystem validation
-    Robot validation

Hardware validation verifies reusable audio abstractions on physical hardware.

Subsystem validation verifies the reusable Audio subsystem using a configured robot implementation.

Robot validation verifies complete audio behavior through the Robot API.

------------------------------------------------------------------------

## Design Principles

The Audio subsystem follows the Betabox Platform Design Principles:

-    Student First
-    Stable Public API
-    Reusable Subsystems
-    Hardware Independence
-    Single Responsibility
-    Explicit Behavior
-    Exclusive Resource Ownership
-    Safe by Default
-    Test Everything

------------------------------------------------------------------------

## Summary

The Audio subsystem provides a stable, reusable interface for speech synthesis, sound playback, tone generation, and melody playback.

It owns the robot's audio resources while exposing convenient Robot API methods for everyday programming and reusable subsystem interfaces for advanced applications.

Higher-level software determines what the robot should say or play.

The Audio subsystem determines how that audio is produced.
