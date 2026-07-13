# Betabox Sensors Subsystem

**Status:** Subsystem Design Specification  
**Project:** Betabox Robot Platform  
**Document:** `sensors.md`

------------------------------------------------------------------------

## Purpose

The Sensors subsystem provides a stable, reusable interface for reading information from the robot and its environment.

It groups individual sensor components under one subsystem while exposing common measurements through the Robot API.

Student code should describe *what information it needs*, not how individual sensors are wired or configured.

------------------------------------------------------------------------

## Robot Composition

The Sensors subsystem is a reusable subsystem implementation composed into a robot implementation.

Robot implementations provide the configuration required to construct the subsystem, including sensor assignments, calibration values, voltage scaling, and hardware dependencies.

Applications should normally access common sensor functionality through the Robot API:

```python
from betabox_robotics import BetaboxCar

with BetaboxCar() as car:
    distance = car.distance()

    if car.is_battery_low():
        car.say("Battery is low")
```

The Sensors subsystem remains available when more detailed control is appropriate:

```python
distance = car.sensors.ultrasonic.distance()

values = car.sensors.grayscale.read()

voltage = car.sensors.battery.voltage()
```

Constructing individual sensor components directly is generally reserved for hardware validation, subsystem validation, testing, and advanced applications.

------------------------------------------------------------------------

## Responsibilities

The Sensors subsystem is responsible for:

### Sensor Access

-    Provide access to supported robot sensors
-    Hide hardware assignments
-    Expose stable sensor APIs

### Sensor Ownership

-    Own sensor component instances
-    Manage sensor lifecycle
-    Release sensor hardware resources during cleanup

### Calibration

-    Apply robot-supplied calibration values
-    Perform sensor-specific calibration
-    Hide calibration details from higher-level code whenever practical

### Physical Units

Return measurements using real-world concepts whenever practical.

Examples include:

-    Centimeters
-    Volts
-    Left, middle, and right grayscale values
-    Normalized grayscale readings

------------------------------------------------------------------------

## Non-Responsibilities

The Sensors subsystem is not responsible for:

-    Driving the robot
-    Obstacle avoidance
-    Line following
-    Autonomous navigation
-    Path planning
-    Vision processing
-    Camera control
-    Audio output
-    User interface behavior

Sensors provide information.

Higher-level software decides how that information should be used.

------------------------------------------------------------------------

## Public API

### Robot API

The Robot API provides convenient access to commonly used sensor measurements.

```python
distance = car.distance()

car.line_values()

car.line_status()

car.line_normalized()

car.battery_voltage()

car.battery_status()

car.is_battery_low()

car.is_battery_critical()
```

### Sensors Subsystem API

The reusable Sensors subsystem remains available for applications requiring more detailed control.

```python
car.sensors.ultrasonic.distance()

car.sensors.grayscale.read()
car.sensors.grayscale.status()
car.sensors.grayscale.normalized()

car.sensors.battery.voltage()
car.sensors.battery.status()
car.sensors.battery.is_low()
car.sensors.battery.is_critical()
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

Measures distance using trigger and echo signals.

Primary API:

```python
distance = car.sensors.ultrasonic.distance()
```

Behavior:

-    Returns distance in centimeters.
-    Handles timeout behavior internally.
-    Supports configurable sampling.
-    Applies robot configuration automatically.
-    Reports invalid configuration through clear Betabox exceptions.

Owns:

-    Trigger pin
-    Echo pin

### Grayscale Sensor

Reads the three-channel line sensor.

Channel order:

-    Left
-    Middle
-    Right

Primary API:

```python
values = car.sensors.grayscale.read()

status = car.sensors.grayscale.status()

normalized = car.sensors.grayscale.normalized()
```

Calibration API:

```python
car.sensors.grayscale.set_calibration(floor, line)

floor, line = car.sensors.grayscale.get_calibration()
```

Behavior:

-    Reads three ADC channels.
-    Returns raw and normalized values.
-    Uses calibration when available.
-    Falls back to documented default behavior otherwise.
-    Reports invalid calibration through clear Betabox exceptions.

Owns:

-    Left ADC
-    Middle ADC
-    Right ADC

### Battery Sensor

Measures battery voltage using the configured ADC channel.

Primary API:

```python
voltage = car.sensors.battery.voltage()

status = car.sensors.battery.status()

car.sensors.battery.is_low()

car.sensors.battery.is_critical()
```

Behavior:

-    Returns voltage in volts.
-    Applies configured voltage scaling.
-    Evaluates configurable battery thresholds.
-    Reports battery state as ok, low, or critical.

Owns:

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

Each sensor component owns the hardware resources required to perform its measurements.

Dependencies always point downward toward reusable hardware abstractions.

------------------------------------------------------------------------

## Resource Ownership

The Sensors subsystem owns its sensor components and coordinates their lifecycle.

During robot cleanup:

-    Ultrasonic releases trigger and echo pins.
-    Grayscale releases ADC channels.
-    Battery releases its ADC channel.

Resource cleanup should not affect Drive, Vision, Audio, or System resources.

Applications should normally allow the robot implementation to coordinate subsystem cleanup automatically.

------------------------------------------------------------------------

## Error Handling

Sensor-specific exceptions should inherit from the appropriate Betabox hardware or sensor exception hierarchy.

Examples include:

-    UltrasonicError
-    GrayscaleError
-    BatteryError

Errors should clearly communicate:

-    Invalid configuration
-    Invalid calibration
-    Invalid timeout
-    Invalid sample count
-    Invalid thresholds
-    Hardware communication failures

Low-level hardware failures should be translated into clear Betabox exceptions whenever practical.

------------------------------------------------------------------------

## Calibration

Calibration belongs to the sensor component that uses it.

Examples:

-    Ultrasonic manages timeout behavior and sampling.
-    Grayscale manages floor and line calibration.
-    Battery manages voltage scaling and threshold evaluation.

Robot-specific calibration values are supplied through configuration rather than embedded within reusable subsystem implementations.

Higher-level behaviors should consume calibrated sensor data rather than duplicate calibration logic.

------------------------------------------------------------------------

## Interaction with Other Subsystems

Sensors provide information to higher-level software.

```text
     Robot API
        │
        ▼
      Sensors
        │
        ▼
 Sensor Components
```

Examples:

```text
    Ultrasonic
        │
        ▼
Obstacle Detection
        │
        ▼
      Drive
```

```text
    Grayscale
       │
       ▼
 Line Following
       │
       ▼
     Drive
```

```text
    Battery
       │
       ▼
System Monitoring
```

Sensors report measurements.

They do not directly control robot behavior.

------------------------------------------------------------------------

## Future Sensors

Future sensor components may include:

-    Wheel encoders
-    IMU
-    GPS
-    Magnetometer
-    Temperature sensor
-    Ambient light sensor
-    Touch sensor
-    Additional distance sensors

Future sensors should follow the same pattern:

```python
car.sensors.<sensor>.<action>()
```

Example:

```python
car.sensors.encoders.left.count()

car.sensors.imu.orientation()
```

Each new sensor should include:

-    Documentation
-    Usage examples
-    Public API documentation
-    Hardware validation
-    Clear cleanup behavior

------------------------------------------------------------------------

## Testing and Validation

The Sensors subsystem should be verified through multiple forms of testing.

These include:

-    Unit tests
-    Hardware validation
-    Subsystem validation
-    Robot validation

Hardware validation verifies reusable sensor abstractions on physical hardware.

Subsystem validation verifies the reusable Sensors subsystem using a configured robot implementation.

Robot validation verifies complete sensor behavior through the Robot API.

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

The Sensors subsystem provides stable, reusable access to physical measurements from the robot and its environment.

It owns and coordinates individual sensor components while exposing convenient Robot API methods for common measurements and reusable subsystem interfaces for advanced applications.

Sensors report information.

Higher-level software decides how the robot should respond.
