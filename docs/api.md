# Betabox Car Public API

**Status:** Public API Specification\
**Project:** Betabox Robot Platform\
**Document:** `api.md`

------------------------------------------------------------------------

## Purpose

This document defines the stable public programming interface for the
Betabox Car SDK.

The public API is the contract used by:

-   Student notebooks
-   Curriculum examples
-   Teacher demonstrations
-   Future web interfaces
-   Internal Betabox applications

Code outside the SDK should interact with the robot through this API
instead of directly using hardware libraries, Linux interfaces, or
implementation-specific modules.

The goal is to allow internal implementations to evolve without breaking
student-facing code.

------------------------------------------------------------------------

## API Philosophy

The Betabox API should be:

-   Stable
-   Student-friendly
-   Hardware-independent
-   Easy to read
-   Easy to teach
-   Explicit in behavior
-   Based on physical robot concepts
-   Safe by default

The API should describe **what** the robot does, not **how** the
hardware accomplishes it.

Example:

``` python
robot.drive.forward(50)
```

is preferred over exposing motors, PWM, GPIO, or other hardware details.

------------------------------------------------------------------------

## Top-Level Robot Object

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

# API Design Rules

Public APIs should:

-   use descriptive names
-   avoid abbreviations
-   avoid exposing hardware details
-   return meaningful Python objects when practical
-   raise Betabox-specific exceptions
-   remain backward compatible whenever possible

------------------------------------------------------------------------

# Drive API

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

# Vision API

Vision provides capabilities rather than exposing camera implementation
details.

Capability groups include:

-   Camera
-   Streaming
-   Detection
-   Recording
-   Snapshots
-   Configuration
-   Statistics
-   Metadata

Illustrative examples:

``` python
robot.vision.start()
robot.vision.stop()

robot.vision.snapshot()

robot.vision.record.start()
robot.vision.record.stop()

robot.vision.stream.start()
robot.vision.stream.stop()

robot.vision.detect.color.enable("red")
robot.vision.detect.color.disable()

robot.vision.metadata.latest()
```

These examples illustrate the intended public interface. Exact method
names may expand over time while preserving the overall API structure.

------------------------------------------------------------------------

# Sensors API

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

------------------------------------------------------------------------

# Audio API

``` python
robot.audio.say("Hello")
robot.audio.play("sound.wav")
robot.audio.stop()
```

------------------------------------------------------------------------

# System API

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

Subsystems own their hardware resources.

Examples:

-   Vision owns the camera.
-   Drive owns motors and steering.
-   Sensors own sensor devices.
-   Audio owns audio hardware.
-   System manages robot services.

Applications should never need to coordinate shared hardware directly.

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

-   BetaboxError
-   HardwareError
-   ConfigurationError
-   ResourceError
-   VisionError
-   DriveError
-   SensorError
-   AudioError

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

``` python
photo = robot.vision.snapshot()
```

``` python
if robot.sensors.battery.is_low():
    print("Battery is low.")
```

``` python
robot.audio.say("Hello, I am Betabox.")
```

------------------------------------------------------------------------

# Internal Implementation Boundary

Applications should not depend on:

-   GPIO
-   PWM
-   I²C implementation details
-   Camera driver objects
-   Linux device paths
-   Streaming protocols
-   Web server internals
-   Calibration files

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
robot.vision.snapshot()
robot.sensors.battery.voltage()
robot.audio.say("Hello")
```

rather than implementation details.
