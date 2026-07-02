# Betabox Drive Subsystem

**Status:** Subsystem Design Specification\
**Project:** Betabox Robot Platform\
**Document:** `drive.md`

------------------------------------------------------------------------

## Purpose

The Drive subsystem is responsible for controlled movement of the robot.

It provides a stable, hardware-independent interface for vehicle motion
while hiding the details of motors, steering mechanisms, PWM
controllers, and board-specific implementations.

Student code should describe **how the robot should move**, not how
individual motors are driven.

------------------------------------------------------------------------

## Robot Composition

The Drive subsystem is a reusable subsystem implementation.

Robot implementations provide the configuration required to initialize
the Drive subsystem.

Applications should normally access movement through:

```python
from betabox_car import Robot

robot = Robot()

robot.drive.forward(50)
```

Constructing the Drive subsystem directly remains appropriate for
validation, testing, and advanced configuration.

Applications should normally interact with Drive through the Robot API.

------------------------------------------------------------------------

## Responsibilities

The Drive subsystem is responsible for:

### Movement

-   Forward movement
-   Backward movement
-   Stopping
-   Controlled speed changes

### Steering

-   Turn left
-   Turn right
-   Center steering
-   Enforce steering limits

### Safety

-   Safe stopping
-   Safe direction changes
-   Speed validation
-   Steering validation

### Robot Configuration

-   Apply robot-specific motor configuration
-   Apply steering limits
-   Apply motor orientation
-   Apply trim values

### State

The Drive subsystem manages the robot's movement state, including
current motion and steering commands.

------------------------------------------------------------------------

## Non-Responsibilities

The Drive subsystem is **not** responsible for:

-   Camera control
-   Vision processing
-   Object detection
-   Line following
-   Obstacle avoidance
-   Autonomous navigation
-   Path planning
-   Audio
-   Lighting
-   System management

Other subsystems may decide *where* the robot should go.

Drive is responsible only for *executing movement safely*.

------------------------------------------------------------------------

## Public API

The public interface is exposed through the Robot API:

``` python
from betabox_car import Robot

robot = Robot()

robot.drive.forward(50)
robot.drive.backward(40)

robot.drive.left(20)
robot.drive.right(20)

robot.drive.center()
robot.drive.stop()
```

The Drive API is intentionally independent of any specific motor
controller or steering hardware.

------------------------------------------------------------------------

## Resource Ownership

The Drive subsystem owns all hardware required for movement.

This includes:

-   Drive motors
-   Steering actuator
-   Movement calibration

The Drive subsystem does **not** own:

-   Camera
-   Pan/Tilt servos
-   Sensors
-   Audio devices
-   LEDs

Other subsystems should never control drive hardware directly.

------------------------------------------------------------------------

## Internal Architecture

``` text
Drive
 ├── Motion
 ├── Steering
 ├── Robot Configuration
 └── Hardware Abstractions
```

Each component has a single responsibility.

Hardware-specific details remain below the public API.

------------------------------------------------------------------------

## Behavior Guarantees

The Drive subsystem should always provide predictable behavior.

Expected guarantees include:

-   `stop()` immediately stops movement.
-   Invalid speed values are rejected or clamped.
-   Steering limits are enforced automatically.
-   Abrupt motor reversals are avoided when possible.
-   Hardware calibration is applied automatically.
-   Internal hardware details remain hidden from user code.

------------------------------------------------------------------------

## Interaction with Other Subsystems

The Drive subsystem accepts movement requests from higher-level
software.

Example interaction:

``` text
     Applications
         │
         ▼
      Robot API
         │
         ▼
       Drive
         │
         ▼
Hardware Abstractions
```

Vision and sensors provide information.

Drive performs movement.

This separation keeps the subsystem focused and reusable.

------------------------------------------------------------------------

## Hardware Independence

Robot-specific wiring and configuration are supplied by the robot implementation rather than the Drive subsystem itself.

The Drive subsystem should not assume any particular implementation.

Possible implementations include:

-   Differential drive
-   Ackermann steering
-   Four-wheel drive
-   Mecanum drive
-   Tracked robots

The public Drive API should remain stable regardless of the underlying
hardware.

------------------------------------------------------------------------

## Implementation Boundary

Implementation details such as:

-   PWM
-   GPIO
-   Motor drivers
-   Servo drivers
-   I²C communication
-   Board layout
-   Robot configuration objects

belong below the Drive subsystem and should never be exposed through the
public API.

------------------------------------------------------------------------

# Design Principles

The Drive subsystem follows the Betabox Platform Design Principles:

- Student First
- Stable Public API
- Reusable Subsystems
- Hardware Independence
- Single Responsibility
- Exclusive Resource Ownership
- Safe by Default
- Test Everything

------------------------------------------------------------------------

## Summary

The Drive subsystem provides a stable interface for robot movement.

Its responsibilities are intentionally limited to executing movement
safely and predictably while hiding hardware complexity.

Higher-level systems determine **what** the robot should do.

The Drive subsystem determines **how** that movement is carried out.
