# Betabox Car Public API

**Status:** Public API Specification\
**Project:** Betabox Robot Platform\
**Document:** `api.md`

------------------------------------------------------------------------

## Purpose

This document defines the stable public programming interface for the
Betabox Car SDK.

The public API is the contract used by:

-    Student notebooks
-    Curriculum examples
-    Teacher demonstrations
-    Future web interfaces
-    Internal Betabox applications

Code outside the SDK should interact with the robot through this API
instead of directly using hardware libraries, Linux interfaces, or
implementation-specific modules.

The goal is to allow internal implementations to evolve without breaking
student-facing code.

------------------------------------------------------------------------

## API Philosophy

The Betabox API should be:

-    Stable
-    Student-friendly
-    Hardware-independent
-    Easy to read
-    Easy to teach
-    Explicit in behavior
-    Based on physical robot concepts
-    Safe by default

The API should describe **what** the robot does, not **how** the
hardware accomplishes it.

Example:

``` python
robot.drive.forward(50)
```

is preferred over exposing motors, PWM, GPIO, or other hardware details.

------------------------------------------------------------------------

## Robot API

The primary entry point is:

``` python
from betabox_car import Robot

robot = Robot()
```

Subsystems:

``` text
Robot
 ├── drive
 ├── vision
 ├── sensors
 ├── audio
 └── system
```

The Robot object is the primary public interface to the platform.

------------------------------------------------------------------------

# Programming Model

The `Robot` object composes reusable subsystem implementations into a
complete robot platform.

Subsystem implementations are independent of any specific robot.

Robot-specific classes are responsible for wiring subsystem
implementations using robot configuration.

This allows future robot platforms (such as robotic arms, tanks, or
drones) to reuse existing subsystem implementations without modifying the
subsystems themselves.

Applications should interact with the `Robot` object rather than
instantiating subsystem implementations directly whenever practical.

------------------------------------------------------------------------

# API Design Rules

Public APIs should:

-    Use descriptive names
-    Avoid abbreviations
-    Avoid exposing hardware details
-    Return meaningful Python objects when practical
-    Raise Betabox-specific exceptions
-    Remain backward compatible whenever possible
-    Prefer capability objects over large monolithic classes
-    Compose reusable subsystem implementations
-    Separate robot configuration from subsystem implementation

------------------------------------------------------------------------

# Subsystem APIs

## Drive API

``` python
robot.drive.forward(speed)
robot.drive.backward(speed)
robot.drive.left(speed)
robot.drive.right(speed)
robot.drive.stop()

robot.drive.steer(angle)
robot.drive.center_steering()
```

The SDK manages steering calibration and limits internally.

------------------------------------------------------------------------

## Vision API

Vision provides capabilities rather than exposing camera implementation
details.

Capability groups include:

-    Camera
-    Streaming
-    Snapshots
-    Recording
-    Detection
-    Metadata
-    Configuration
-    Statistics

### Snapshots

```python
snapshot = robot.vision.snapshot.capture()
print(snapshot.path)
```

### Recording

```python
robot.vision.recording.start()

# ...

recording = robot.vision.recording.stop()

print(recording.path)
print(recording.duration)
```

### Streaming

```python
robot.vision.stream.start()
robot.vision.stream.stop()
```

### Detection

#### Color

```python
robot.vision.detection.color.enable("red")

metadata = robot.vision.metadata.latest("color")
```

#### Face

```python
robot.vision.detection.face.enable()

metadata = robot.vision.metadata.latest("face")
```

Implemented capabilities:

-    Color
-    Face

Planned capabilities:

-    Object
-    Traffic Sign

Detection capabilities are exposed as capability objects rather than
requiring applications to create or register detector instances.

## Sensors API

``` python
robot.sensors.ultrasonic.distance()

robot.sensors.grayscale.read()
robot.sensors.grayscale.status()

robot.sensors.battery.voltage()
robot.sensors.battery.status()
robot.sensors.battery.is_low()
robot.sensors.battery.is_critical()
```

Future sensors should follow:

``` python
robot.sensors.<sensor>.<action>()
```

## Audio API

The Audio subsystem provides speech synthesis, sound playback, tone
generation, and melody playback.

### Speech

```python
robot.audio.say("Hello from Betabox")
```

Optional speech configuration is available when using `Audio` directly:

```python
from betabox_car.audio import Audio

audio = Audio(
    speech_engine="pico",
    speech_volume=1.8,
)
```

Piper is supported as an optional high-quality speech backend:

```python
audio = Audio(
    speech_engine="piper",
    piper_voice="en_US-amy-low",
)
```

### Sound Playback

```python
robot.audio.play_sound("car-honk")
```

Alias:

```python
robot.audio.play("car-honk")
```

### Tone Playback

```python
robot.audio.play_note("C5", 0.5)
robot.audio.play_note(440.0, 0.5)
```

### Melody Playback

```python
robot.audio.play_melody(
    [
        ("C5", 0.2),
        ("D5", 0.2),
        ("E5", 0.2),
        ("G5", 0.4),
    ],
    gap=0.05,
)
```

### Playback Control

```python
robot.audio.stop()
```

### Diagnostics

```python
robot.audio.speech_backend_name
robot.audio.available_speech_backends()
```

Audio hides implementation details such as PyAudio, ALSA, speech engines,
audio conversion tools, and amplifier GPIO control.

## System API

``` python
status = robot.system.status()
```

Representative fields:

``` text
hostname
ip_address
battery
camera_running
services
```

------------------------------------------------------------------------

# Resource Management

Robot implementations compose reusable subsystem implementations and provide the configuration required to initialize them.

Subsystems own the hardware resources they manage.

Examples:

-    Vision owns the camera.
-    Drive owns motors and steering.
-    Sensors own sensor devices.
-    Audio owns audio hardware.
-    System owns platform services and status information.

Applications should never need to coordinate shared hardware directly.

Applications should normally interact with subsystem instances provided
by the `Robot` object rather than constructing additional subsystem
instances directly.

Applications should enable capabilities rather than creating additional subsystem instances. The SDK manages the lifecycle of shared resources such as the camera.

------------------------------------------------------------------------

# Thread Safety

Subsystem objects are intended to be long-lived.

Background processing is managed internally by the SDK.

Student code should not need to create threads to use robot
capabilities.

------------------------------------------------------------------------

# Error Handling

Public APIs should raise Betabox-specific exceptions.

Examples:

-    BetaboxError
-    HardwareError
-    ConfigurationError
-    ResourceError
-    VisionError
-    DriveError
-    SensorError
-    AudioError

Errors should explain what happened and, when possible, how the user can
resolve the issue.

Implementation-specific exceptions should not leak into the public API.

------------------------------------------------------------------------

# API Versioning

Breaking API changes should only occur during major SDK releases.

Minor releases should preserve compatibility with existing notebooks
whenever practical.

------------------------------------------------------------------------

# Student Examples

``` python
from betabox_car import Robot

robot = Robot()
robot.drive.forward(50)
robot.drive.stop()
```

```python
if robot.sensors.battery.is_low():
    print("Battery is low.")
```

```python
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
```

``` python
snapshot = robot.vision.snapshot.capture()
print(snapshot.path)
```

```python
from time import sleep

robot.vision.recording.start()

sleep(5)

recording = robot.vision.recording.stop()

print(recording.path)
```

```python
robot.vision.detection.color.enable(["red", "green"])

metadata = robot.vision.metadata.latest("color")

print(metadata.data["counts"])
```

```python
robot.vision.detection.face.enable()

metadata = robot.vision.metadata.latest("face")

print(metadata.data["count"])
```

```python
from betabox_car import Robot

robot = Robot()

robot.drive.forward(40)

distance = robot.sensors.ultrasonic.distance()

if distance < 20:
    robot.drive.stop()
    robot.audio.say("Obstacle detected.")
```

------------------------------------------------------------------------

# Implementation Boundary

Robot-specific configuration is an implementation detail and should not be accessed directly by applications.

Applications should not depend on:

-    GPIO
-    PWM
-    I²C implementation details
-    Camera driver objects
-    Linux device paths
-    Streaming protocols
-    Web server internals
-    Calibration files
-    Audio driver objects
-    Speech engine commands
-    Audio conversion tools
-    Speaker amplifier GPIO control
-    Robot configuration objects

Packages under `hardware/`, `vision/`, `drive/`, `sensors/`, and other
implementation modules are internal unless explicitly documented as
public.

Applications should interact with the platform through the Robot API.

------------------------------------------------------------------------

# Summary

The Robot API is the stable boundary between user code and robot
implementation.

Students should think in terms of robot behavior:

``` python
robot.drive.forward(50)
robot.vision.snapshot.capture()
robot.vision.recording.start()
robot.vision.detection.color.enable("red")
robot.sensors.battery.voltage()
robot.audio.say("Hello")
```

rather than implementation details.
