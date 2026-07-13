# Betabox Robotics Public API

**Status:** Public API Specification\
**Project:** Betabox Robotics Platform\
**Audience:** Students, Teachers, Developers\
**Document:** `api.md`

------------------------------------------------------------------------

## Purpose

The Betabox Robotics SDK exposes a stable, beginner-friendly API for
programming educational robots.

The SDK is designed to:

-   Hide hardware implementation details.
-   Present robots in terms of capabilities.
-   Remain stable across SDK releases.
-   Support both beginner and advanced users.
-   Allow robot implementations to evolve without breaking curriculum.

Applications should program **robots**, not GPIO pins, motors, cameras,
or operating-system services.

------------------------------------------------------------------------

## Design Philosophy

The SDK intentionally exposes two complementary API layers.

### 1. Robot API (Recommended)

The Robot API provides high-level robot capabilities through concrete robot implementations.

Current robot implementations include:

-    BetaboxCar

Future robot implementations may include:

-    BetaboxArm
-    BetaboxTank
-    BetaboxDrone

Example:

``` python
from betabox_robotics import BetaboxCar

with BetaboxCar() as car:
    car.forward(40)

    if car.distance() < 20:
        car.stop()
        car.say("Obstacle detected")
```

The Robot API is intended for:

-    Students
-    Curriculum
-    Classroom examples
-    Teacher demonstrations
-    Most applications

### 2. Subsystem API

Advanced users may access the robot's reusable subsystem interfaces for finer-grained control while remaining hardware-independent.

``` python
car.drive.forward(40)
car.audio.say("Hello")
car.sensors.ultrasonic.distance()
car.vision.capture("photo.jpg")
```

The subsystem API exposes additional capabilities without requiring applications to communicate directly with hardware.

------------------------------------------------------------------------

## Programming Model

Robot implementations compose reusable subsystem interfaces.

BetaboxCar
 ├── Drive
 ├── Sensors
 ├── Vision
 ├── Audio
 └── System

The Robot API delegates common operations to these subsystem interfaces while providing convenient top-level methods for everyday programming.

Applications should normally interact with the Robot API unless more detailed control is required.

------------------------------------------------------------------------

## Lifecycle

Robot implementations manage hardware resources and support Python context managers.

The recommended usage pattern is:

``` python
from betabox_robotics import BetaboxCar

with BetaboxCar() as car:
    car.forward(40)
```

When the context exits, the robot automatically releases owned hardware resources.

Robots may also be managed manually:

``` python
car = BetaboxCar()

try:
    car.forward(40)
finally:
    car.close()
```

------------------------------------------------------------------------

## Robot API

### Movement

``` python
car.forward(speed)
car.backward(speed)

car.left(angle=30)
car.right(angle=30)

car.center()
car.stop()
```

Example:

``` python
car.forward(35)
car.left()
car.stop()
```

### Audio

``` python
car.say(text)

car.play(sound)

car.play_note(note_or_frequency, duration)

car.play_melody(notes, gap=0.0)

car.stop_audio()

car.is_audio_playing()
```

### Sensors

#### Distance

``` python
distance = car.distance()
```

#### Battery

``` python
car.battery_voltage()

car.battery_status()

car.is_battery_low()

car.is_battery_critical()
```

#### Line Sensor

``` python
car.line_values()

car.line_status()

car.line_normalized()
```

### Vision

Vision must be started before capturing or recording.

``` python
car.start_vision()

car.is_vision_running()

snapshot = car.capture("photo.jpg")

car.start_recording("demo.mp4")

recording = car.stop_recording()

car.is_recording()

car.stop_vision()
```

### System

``` python
car.hostname()

car.ip_addresses()

car.media_paths()

car.ensure_media_paths()

car.status()

car.health()
```

------------------------------------------------------------------------

## Subsystem API

The reusable subsystem interfaces remain fully available.

### Drive

``` python
car.drive.forward(speed)
car.drive.backward(speed)

car.drive.left(angle)
car.drive.right(angle)

car.drive.center()

car.drive.stop()
```

### Sensors

``` python
car.sensors.ultrasonic.distance()

car.sensors.grayscale.read()
car.sensors.grayscale.status()
car.sensors.grayscale.normalized()

car.sensors.battery.voltage()
car.sensors.battery.status()
car.sensors.battery.is_low()
car.sensors.battery.is_critical()
```

### Vision

``` python
car.vision.start()
car.vision.stop()

car.vision.snapshot.capture(filename="photo.jpg")

car.vision.recording.start(filename="demo.mp4")
car.vision.recording.stop()
```

Lower-level detection, metadata, streaming, and frame APIs remain
available for advanced applications.

### Audio

``` python
car.audio.say("Hello")

car.audio.play("success.wav")

car.audio.play_note("C5", 0.5)

car.audio.play_melody([...])

car.audio.stop()
```

### System

``` python
car.system.status()
car.system.health()
```

------------------------------------------------------------------------

## Resource Ownership

Each subsystem owns the hardware resources it manages.

  Subsystem   Owns
  ----------- ----------------------
  Drive       Motors, steering
  Sensors     Physical sensors
  Vision      Camera pipeline
  Audio       Audio playback
  System      Platform information and services

Applications should not create competing objects that access the same hardware resources directly.

Resource ownership is coordinated by the robot implementation.

------------------------------------------------------------------------

## API Design Rules

The Robot API should:

-    Prefer robot capabilities over implementation details.
-    Use descriptive names.
-    Hide hardware details.
-    Be safe by default.
-    Remain backward compatible whenever practical.
-    Keep beginner code readable.

Not every subsystem method belongs on the Robot API.

Top-level convenience methods should represent common robot tasks rather than mirror every subsystem capability.

Advanced functionality should remain available through documented subsystem interfaces.

Example:

``` python
from time import sleep
from betabox_robotics import BetaboxCar

with BetaboxCar() as car:
    car.say("Starting demo")

    car.start_vision()
    sleep(1)

    car.forward(30)
    sleep(1)
    car.stop()

    print(car.distance())

    photo = car.capture("picture.jpg")
    print(photo.path)

    if car.is_battery_low():
        car.say("Battery is low")
```

------------------------------------------------------------------------

## Stability

The Robot API forms the stable boundary between user applications and robot implementations.

Future robot platforms may expose different concrete robot classes, such as BetaboxArm or BetaboxTank, while preserving the same architectural principles, subsystem design, and programming model.

Student notebooks, curriculum, and classroom examples should primarily depend on the Robot API. Advanced applications may use documented subsystem interfaces when finer control is required.

Internal implementation details are not considered part of the public API and may change without notice.
