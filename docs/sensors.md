# Betabox Sensors Subsystem

**Status:** Subsystem Design Specification  
**Project:** Betabox Robot Platform  
**Document:** `sensors.md`

------------------------------------------------------------------------

## Purpose

The Sensors subsystem provides a stable interface for reading information from the physical robot environment.

It groups individual sensor components under one subsystem so student code can access sensor data through the public Robot API instead of directly managing hardware objects.

Student code should describe **what information it needs**, not how the sensor hardware is wired.

------------------------------------------------------------------------

## Robot Composition

The Sensors subsystem is a reusable subsystem implementation.

Robot implementations provide the sensor configuration required to
initialize the subsystem.

Applications should normally access sensors through:

```python
from betabox_car import Robot

robot = Robot()

distance = robot.sensors.ultrasonic.distance()
```

rather than constructing sensor components directly.

Constructing individual sensor components remains appropriate for
validation, testing, and advanced configuration.

------------------------------------------------------------------------

## Responsibilities

The Sensors subsystem is responsible for:

### Sensor Access

-    Provide access to supported robot sensors
-    Hide default pin and channel mappings
-    Expose sensor readings through stable APIs

### Sensor Ownership

-    Own sensor component instances
-    Manage sensor lifecycle
-    Release sensor hardware resources during cleanup

### Calibration

-    Support sensor-specific calibration where needed
-    Keep calibration logic close to the sensor that uses it
-    Hide raw calibration details from high-level code when possible

### Physical Units

-    Return readings in student-friendly units
-    Prefer real-world concepts over raw hardware values where practical

Examples:

-    Centimeters for ultrasonic distance
-    Left/middle/right channel values for grayscale readings
-    Normalized grayscale values when calibrated
-    Volts for battery monitoring

------------------------------------------------------------------------

## Non-Responsibilities

The Sensors subsystem is **not** responsible for:

-    Driving the robot
-    Obstacle avoidance behavior
-    Line following behavior
-    Autonomous navigation
-    Path planning
-    Vision processing
-    Camera control
-    Audio output
-    User interface behavior

Sensors provide information.

Higher-level logic decides what to do with that information.

------------------------------------------------------------------------

## Public API

Individual sensor components may also be used directly by robot implementations, validation programs, or advanced applications that provide the required hardware dependencies.

```python
from betabox_car import Robot

robot = Robot()

distance = robot.sensors.ultrasonic.distance()

values = robot.sensors.grayscale.read()

voltage = robot.sensors.battery.voltage()
```

------------------------------------------------------------------------

## Components

The current Sensors subsystem includes:

```text
Sensors
 ├── Ultrasonic
 ├── Grayscale
 └── Battery
```

### Ultrasonic Sensor

The Ultrasonic sensor measures distance using a trigger pin and echo pin.

Public API:

```python
distance = robot.sensors.ultrasonic.distance()
```

Compatibility API:

```python
distance = robot.sensors.ultrasonic.read()
```

Expected behavior:

-    Distance is returned in centimeters.
-    Timeout behavior is handled internally.
-    Trigger and echo pins are supplied by the robot implementation through robot configuration.
-    Invalid sample counts raise a clear sensor error.

The Ultrasonic component owns:

-    Trigger pin
-    Echo pin

### Grayscale Sensor

The Grayscale sensor reads a three-channel line sensor.

Channels are ordered:

```text
left, middle, right
```

Public API:

```python
values = robot.sensors.grayscale.read()
status = robot.sensors.grayscale.status()
```

Calibration API:

```python
robot.sensors.grayscale.set_calibration(floor, line)
floor, line = robot.sensors.grayscale.get_calibration()
normalized = robot.sensors.grayscale.normalized()
```

Compatibility API:

```python
status = robot.sensors.grayscale.read_status()
normalized = robot.sensors.grayscale.get_grayscale_normalized()
```

Expected behavior:

-    Raw values are read from three ADC channels.
-    Status returns `0` for floor and `1` for line.
-    If floor/line calibration is available, normalized values are used.
-    If calibration is not available, legacy reference thresholds are used.
-    Invalid channel or calibration input raises a clear sensor error.

The Grayscale component owns:

-    Left ADC channel
-    Middle ADC channel
-    Right ADC channel

### Battery Sensor

The Battery sensor measures battery voltage using the configured ADC channel.

Public API:

```python
voltage = robot.sensors.battery.voltage()
status = robot.sensors.battery.status()

robot.sensors.battery.is_low()
robot.sensors.battery.is_critical()
```

Compatibility API:

```python
voltage = robot.sensors.battery.read()
```

Expected behavior:

-    Voltage is returned in volts.
-    The robot-configured voltage-divider scale factor is applied automatically.
-    Low and critical battery thresholds are configurable.
-    Battery state is reported as `ok`, `low`, or `critical`.

The Battery component owns:

-    Battery ADC channel

------------------------------------------------------------------------

## Internal Architecture

```text
Sensors
 ├── Ultrasonic
 │    ├── Trigger Pin
 │    └── Echo Pin
 │
 ├── Grayscale
 │    ├── Left ADC
 │    ├── Middle ADC
 │    └── Right ADC
 │
 └── Battery
      └── Battery ADC
```

The Sensors subsystem owns the sensor components.

Each sensor component owns the hardware resources it requires.

Dependencies always point downward.

------------------------------------------------------------------------

## Resource Ownership

The Sensors subsystem owns sensor components and is responsible for closing them.

Example:

```python
robot.sensors.close()
```

Expected cleanup behavior:

-    Ultrasonic trigger and echo pins are closed.
-    Grayscale ADC channels are closed.
-    Battery ADC channel is closed.
-    Releasing sensors should not affect unrelated subsystems.

Sensors should not control hardware owned by Drive, Vision, Audio, or System.

------------------------------------------------------------------------

## Error Handling

Sensor-specific errors should inherit from a Betabox hardware or sensor error type.

Current sensor errors include:

```python
UltrasonicError
GrayscaleError
BatteryError
```

Errors should be clear and actionable.

Examples:

-    Invalid channel
-    Invalid calibration values
-    Invalid timeout
-    Invalid sample count
-    Invalid battery thresholds

Low-level hardware exceptions should be wrapped or presented in a student-readable way where possible.

------------------------------------------------------------------------

## Calibration

Calibration belongs to the sensor component that uses it.

Examples:

-    Grayscale handles floor/line calibration.
-    Ultrasonic handles timeout behavior and sample attempts.
-    Battery handles voltage scaling and threshold evaluation.

Higher-level behaviors such as line following or obstacle avoidance should use calibrated sensor data rather than duplicating calibration logic.

------------------------------------------------------------------------

## Interaction with Other Subsystems

Sensors provide information to higher-level code.

```text
   Applications
        │
        ▼
     Robot API
        │
        ▼
     Sensors
        │
        ▼
Sensor Components
```

Example:

```text
   Ultrasonic
       │
       ▼
Obstacle Avoidance Logic
       │
       ▼
     Drive
```

Example:

```text
    Grayscale
       │
       ▼
Line Following Logic
       │
       ▼
     Drive
```

Example:

```text
    Battery
       │
       ▼
System Monitoring
```

Sensors do not directly command Drive.

This keeps sensor reading separate from robot behavior.

------------------------------------------------------------------------

## Future Sensors

Future sensors may include:

-    Wheel encoders
-    IMU
-    GPS
-    Magnetometer
-    Temperature sensor
-    Additional distance sensors

Future sensors should follow the same pattern:

```python
robot.sensors.<sensor>.<action>()
```

Examples:

```python
robot.sensors.encoders.left.count()
robot.sensors.imu.orientation()
```

Each new sensor should include:

-    Documentation
-    Example program
-    Public API
-    Hardware validation
-    Clear cleanup behavior

------------------------------------------------------------------------

## Design Principles

The Sensors subsystem follows the Betabox Platform Design Principles:

-    Student First
-    Stable Public API
-    Reusable Subsystems
-    Hardware Independence
-    Single Responsibility
-    Physical Units
-    Exclusive Resource Ownership
-    Safe by Default
-    Test Everything

------------------------------------------------------------------------

## Summary

The Sensors subsystem provides the robot with access to physical environment data.

It owns and organizes individual sensor components while hiding hardware details from student code.

Sensors report information.

Higher-level systems decide how the robot should respond.
