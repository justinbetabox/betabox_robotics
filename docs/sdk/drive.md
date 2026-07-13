# Betabox Drive Subsystem

**Status:** Subsystem Design Specification\
**Project:** Betabox Robot Platform\
**Document:** `drive.md`

------------------------------------------------------------------------

## Purpose

The Drive subsystem is responsible for controlled movement of the robot.

It provides a stable, reusable, hardware-independent interface for robot motion while hiding the details of motors, steering mechanisms, PWM controllers, and board-specific implementations.

Student code should describe how the robot should move, not how individual motors or controllers operate.

------------------------------------------------------------------------

## Robot Composition

The Drive subsystem is a reusable subsystem implementation composed into a robot implementation.

Robot implementations supply the configuration required to construct the Drive subsystem, including motor orientation, steering limits, calibration, and hardware assignments.

Applications should normally access movement through the Robot API:

```python
from betabox_robotics import BetaboxCar

with BetaboxCar() as car:
    car.forward(50)
    car.left()
```

The Drive subsystem remains available when more detailed control is appropriate:

```python
car.drive.forward(50)
car.drive.left(20)
```

Constructing the Drive subsystem directly is generally reserved for hardware validation, subsystem validation, testing, and advanced applications.

------------------------------------------------------------------------

## Responsibilities

The Drive subsystem is responsible for:

### Movement

-    Forward movement
-    Backward movement
-    Stopping
-    Controlled speed changes

### Steering

-    Turn left
-    Turn right
-    Center steering
-    Enforce steering limits

### Safety

-    Safe stopping
-    Safe direction changes
-    Speed validation
-    Steering validation

### Configuration

-    Apply robot-specific motor configuration
-    Apply steering limits
-    Apply motor orientation
-    Apply trim values
-    Apply calibration

### State

The Drive subsystem manages the robot's movement state, including
current motion and steering commands.

------------------------------------------------------------------------

## Non-Responsibilities

The Drive subsystem is **not** responsible for:

-    Camera control
-    Vision processing
-    Object detection
-    Line following
-    Obstacle avoidance
-    Autonomous navigation
-    Path planning
-    Audio
-    Lighting
-    System management

Higher-level software determines what the robot should do.

The Drive subsystem is responsible only for *executing movement safely and predictably*.

------------------------------------------------------------------------

## Public API

### Robot API

The Robot API provides convenient movement methods intended for most applications.

``` python
car.forward(speed)
car.backward(speed)

car.left(angle=30)
car.right(angle=30)

car.center()
car.stop()
```

These methods delegate to the Drive subsystem.

### Drive Subsystem API

The reusable Drive subsystem remains available for applications requiring more detailed control.

``` python
car.drive.forward(speed)
car.drive.backward(speed)

car.drive.left(angle)
car.drive.right(angle)

car.drive.center()
car.drive.stop()
```

The Drive API remains independent of any specific motor controller, steering hardware, or robot platform.

------------------------------------------------------------------------

## Resource Ownership

The Drive subsystem owns all hardware required for movement.

This includes:

-    Drive motors
-    Steering actuator
-    Movement calibration
-    Active drive configuration

The Drive subsystem does **not** own:

-    Camera
-    Pan/Tilt servos
-    Sensors
-    Audio devices
-    LEDs

Applications and other subsystems should never control drive hardware directly.

------------------------------------------------------------------------

## Internal Architecture

``` text
Drive
 ├── Motor
 ├── Steering
 └── Robot Configuration
```

The Drive subsystem composes reusable hardware abstractions while hiding implementation details from higher layers.

Hardware interfaces, controllers, PWM, GPIO, I²C, and operating-system interactions remain below the subsystem boundary.

------------------------------------------------------------------------

## Behavior Guarantees

The Drive subsystem should provide predictable behavior.

Expected guarantees include:

-    stop() immediately stops movement.
-    Speed values are handled according to the documented API contract.
-    Steering limits are enforced automatically.
-    Abrupt motor reversals are avoided whenever practical.
-    Robot calibration is applied automatically.
-    Hardware implementation details remain hidden from applications.

------------------------------------------------------------------------

## Interaction with Other Subsystems

The Drive subsystem accepts movement requests from higher-level software.

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

Other subsystems provide information.

Examples include:

-    Vision detects an obstacle.
-    Sensors measure distance.
-    System reports battery status.

The Drive subsystem executes the requested movement.

This separation keeps the subsystem reusable, testable, and focused on one responsibility.

------------------------------------------------------------------------

## Hardware Independence

Drive receives robot-specific configuration during construction.

It should not import robot-specific configuration directly.

Possible robot implementations include:

-    Differential drive
-    Ackermann steering
-    Four-wheel drive
-    Mecanum drive
-    Tracked robots

The public Drive API should remain stable regardless of the underlying hardware implementation.

------------------------------------------------------------------------

## Implementation Details

Implementation details such as:

-    PWM
-    GPIO
-    Motor drivers
-    Servo drivers
-    I²C communication
-    Board layout
-    Robot configuration objects

remain below the Drive subsystem and are not exposed through the public API.

------------------------------------------------------------------------

# Design Principles

The Drive subsystem follows the Betabox Platform Design Principles:

-    Student First
-    Stable Public API
-    Composition over Inheritance
-    Reusable Subsystems
-    Hardware Independence
-    Single Responsibility
-    Explicit Behavior
-    Exclusive Resource Ownership
-    Safe by Default
-    Test Everything

------------------------------------------------------------------------

## Testing and Validation

The Drive subsystem should be verified through multiple forms of testing.

These include:

-    Unit tests
-    Hardware validation
-    Subsystem validation
-    Robot validation

Hardware validation verifies reusable drive hardware abstractions.

Subsystem validation verifies the reusable Drive subsystem using a configured robot implementation.

Robot validation verifies complete robot movement through the Robot API.

## Summary

The Drive subsystem provides a stable, reusable interface for robot movement.

Its responsibility is intentionally limited to executing movement safely and predictably while hiding hardware complexity.

Robot implementations compose the Drive subsystem into complete robots, while the Robot API exposes convenient movement methods for everyday programming.

This separation allows the movement system to evolve internally while preserving a stable, easy-to-use programming interface.
