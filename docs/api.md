# Betabox Car Public API

**Status:** Draft Public API Specification  
**Project:** Betabox Robot Platform  
**Document:** `api.md`

---

## Purpose

This document defines the public programming interface for the Betabox Car SDK.

The public API is the contract used by:

- Student notebooks
- Curriculum examples
- Teacher demonstrations
- Future web interfaces
- Internal Betabox applications

Code outside the SDK should interact with the robot through this API instead of directly using hardware libraries, Linux interfaces, or implementation-specific modules.

The goal is to allow the internal implementation to change without breaking student-facing or curriculum-facing code.

---

## API Philosophy

The Betabox API should be:

- Stable
- Student-friendly
- Hardware-independent
- Easy to read
- Easy to teach
- Explicit in behavior
- Based on physical robot concepts
- Safe by default

The API should describe what the robot does, not how the hardware does it.

For example:

```python
robot.drive.forward(50)
```

is preferred over exposing low-level motor, PWM, or GPIO details.

---

## Top-Level Robot Object

The primary entry point is the `Robot` object.

```python
from betabox_car import Robot

robot = Robot()
```

The `Robot` object exposes major subsystems:

```python
robot.drive
robot.vision
robot.sensors
robot.audio
robot.system
```

Each subsystem is responsible for one area of robot behavior.

---

## Subsystem Overview

```text
Robot
 ├── drive
 ├── vision
 ├── sensors
 ├── audio
 └── system
```

The public API should remain stable even if the internal hardware implementation changes.

---

# Drive API

The Drive API controls robot movement.

## Basic Movement

```python
robot.drive.forward(speed)
robot.drive.backward(speed)
robot.drive.left(speed)
robot.drive.right(speed)
robot.drive.stop()
```

## Steering

```python
robot.drive.steer(angle)
robot.drive.center_steering()
```

The SDK manages steering limits and calibration internally.

---

# Vision API

The Vision API controls camera, streaming, snapshots, recording, and detection.

```python
robot.vision
```

The public API intentionally hides camera implementation details such as transport protocols or Linux camera drivers.

---

# Sensors API

The Sensors API provides access to robot sensors.

```python
robot.sensors
```

---

## Ultrasonic Sensor

```python
robot.sensors.ultrasonic.distance()
```

---

## Grayscale Sensor

```python
robot.sensors.grayscale.read()
robot.sensors.grayscale.status()
```

---

## Battery Sensor

```python
voltage = robot.sensors.battery.voltage()
status = robot.sensors.battery.status()

robot.sensors.battery.is_low()
robot.sensors.battery.is_critical()
```

Compatibility API:

```python
robot.sensors.battery.read()
```

Battery state is reported as:

- `ok`
- `low`
- `critical`

Voltage is returned in volts.

---

## Future Sensors

Future sensors may include:

```python
robot.sensors.imu
robot.sensors.encoders
```

These should follow the same pattern:

```python
robot.sensors.<sensor>.<action>()
```

---

# Audio API

```python
robot.audio.say("Hello")
robot.audio.play("sound.wav")
robot.audio.stop()
```

---

# System API

```python
robot.system
```

## Status

```python
status = robot.system.status()

status.hostname
status.ip_address
status.battery
status.camera_running
status.services
```

---

# Error Handling

The public API should raise clear Betabox-specific exceptions.

Examples:

```python
BetaboxError
HardwareError
ConfigurationError
ResourceError
VisionError
DriveError
SensorError
AudioError
```

---

# Resource Ownership

Shared hardware resources should have one owner.

Examples:

- Vision owns the camera.
- Drive owns motors and steering.
- Sensor components own their hardware resources.
- System manages background robot services.

---

# API Stability Promise

The public API should change slowly and intentionally.

Internal implementations may evolve as long as the public API remains stable.

---

# Student Examples

## Basic Driving

```python
from betabox_car import Robot
from time import sleep

robot = Robot()

robot.drive.forward(50)
sleep(2)
robot.drive.stop()
```

---

## Obstacle Avoidance

```python
from betabox_car import Robot
from time import sleep

robot = Robot()

while True:
    distance = robot.sensors.ultrasonic.distance()

    if distance < 20:
        robot.drive.stop()
        robot.drive.backward(40)
        sleep(1)
        robot.drive.stop()
    else:
        robot.drive.forward(40)
```

---

## Battery Monitoring

```python
from betabox_car import Robot

robot = Robot()

print(robot.sensors.battery.voltage())
print(robot.sensors.battery.status())

if robot.sensors.battery.is_low():
    print("Battery is low.")
```

---

## Take a Snapshot

```python
from betabox_car import Robot

robot = Robot()

robot.vision.start()
photo = robot.vision.snapshot()

print(photo.path)
```

---

## Color Detection

```python
from betabox_car import Robot
from time import sleep

robot = Robot()

robot.vision.start()
robot.vision.detect.color.enable("red")

while True:
    result = robot.vision.detect.color.get()

    if result.count > 0:
        print("I see red!")

    sleep(0.1)
```

---

## Voice Output

```python
from betabox_car import Robot

robot = Robot()

robot.audio.say("Hello, I am Betabox.")
```

---

# Internal Implementation Boundary

Student-facing code should never need to know about:

- GPIO
- PWM
- I²C details
- Camera driver objects
- Linux device paths
- Streaming protocol internals
- Web server internals
- Hardware calibration files

Those implementation details belong inside the SDK.

---

# Summary

The Betabox Car Public API is the stable boundary between user code and robot implementation.

Students should think in terms of robot behavior:

```python
robot.drive.forward(50)
robot.vision.snapshot()
robot.sensors.battery.voltage()
robot.audio.say("Hello")
```

rather than hardware implementation details.
