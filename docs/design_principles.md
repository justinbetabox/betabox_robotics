# Betabox Platform Design Principles

**Status:** Foundational Design Principles\
**Project:** Betabox Robot Platform

------------------------------------------------------------------------

## Purpose

This document defines the core principles that guide the design of the
Betabox platform.

Every subsystem, API, service, and hardware abstraction should follow
these principles. When implementation decisions conflict with these
principles, the implementation should be reconsidered before the
principles are changed.

------------------------------------------------------------------------

## 1. Student First

Public APIs should read naturally and be easy for beginners to
understand.

``` python
robot.drive.forward(50)
robot.vision.snapshot()
robot.audio.say("Hello")
```

Students should think about **robot behavior**, not hardware
implementation.

------------------------------------------------------------------------

## 2. Stable Public API

The public API is the long-term contract between the platform and user
code.

Student notebooks, curriculum, and applications should continue working
even as the internal implementation evolves.

------------------------------------------------------------------------

## 3. Robot Behavior over Hardware Behavior

The public API should describe what the robot should do rather than how
individual hardware components operate.

Examples:

Good:

-    robot.drive.forward(50)
-    robot.audio.say("Hello")
-    robot.vision.snapshot.capture()

Avoid exposing:

-    GPIO pins
-    PWM channels
-    Linux device paths
-    Speech engine commands
-    Camera driver objects

------------------------------------------------------------------------

## 4. Hardware Independence

User code should never depend on a specific board, operating system,
driver, or communication protocol.

Hardware may change.

The API should not.

------------------------------------------------------------------------

## 5. Composition over Inheritance

Subsystems should be built from smaller components with well-defined
responsibilities.

Examples:

-   Servo owns PWM
-   PWM owns I2C
-   Drive owns Motors
-   Vision owns the Camera
-   Robot owns all major subsystems

------------------------------------------------------------------------

## 6. Reusable Subsystems

Subsystem implementations should be reusable across multiple robot
platforms.

Robot-specific behavior belongs in robot implementations rather than
inside reusable subsystems.

Examples:

-    Drive should not know which robot it belongs to.
-    Audio should not depend on a specific speaker implementation.
-    Sensors should not assume a particular wiring configuration.

This separation allows new robot platforms to reuse existing subsystem
implementations without modification.

------------------------------------------------------------------------

## 7. Dependency Direction

Dependencies should always flow from robot-specific implementations
toward reusable subsystem implementations.

```text
   Applications
        │
        ▼
     Robot API
        │
        ▼
Robot Implementation
        │
        ▼
Reusable Subsystems
        │
        ▼
Hardware Abstractions
```

Reusable subsystem implementations should never depend on robot-specific
configuration.

------------------------------------------------------------------------

## 8. Single Responsibility

Every class, module, and subsystem should have one clearly defined
purpose.

Responsibilities should not overlap.

------------------------------------------------------------------------

## 9. Stable Subsystems

Each major subsystem should provide a clear, stable interface.

Current subsystems include:

-   Drive
-   Vision
-   Sensors
-   Audio
-   System

Subsystems should communicate through well-defined interfaces rather
than implementation details.

Subsystems should remain reusable across robot implementations.

------------------------------------------------------------------------

## 10. Explicit Behavior

The platform should never silently change hardware state or perform
unexpected actions.

Behavior should be predictable and easy to understand.

------------------------------------------------------------------------

## 11. Physical Units

Public APIs should use real-world units whenever possible.

Examples:

-   Degrees
-   Percent speed
-   Centimeters
-   Volts
-   Seconds

Students should not need to understand hardware register values or
timing calculations.

------------------------------------------------------------------------

## 12. Hide Complexity

Implementation details should remain inside the platform.

Examples include:

-   GPIO
-   PWM
-   I²C
-   Camera drivers
-   Linux interfaces
-   Streaming protocols
-   Hardware calibration

Students should interact with robot concepts instead of low-level
hardware.

------------------------------------------------------------------------

## 13. Exclusive Resource Ownership

Shared hardware resources should have one owner.

Examples include:

-   Camera
-   Drive motors
-   Audio device

Other components access these resources through the owning subsystem
rather than opening hardware directly.

------------------------------------------------------------------------

## 14. Safe by Default

The platform should choose the safest reasonable behavior.

Examples include:

-   Clamping invalid values
-   Preventing abrupt motor reversals
-   Recovering gracefully from hardware failures
-   Protecting shared resources

------------------------------------------------------------------------

## 15. Test Everything

Every public component should include:

-    Documentation
-    Usage examples
-    Unit tests where practical
-    Hardware validation
-    Subsystem validation
-    Robot validation (when applicable)

A feature is not considered complete until it can be confidently
verified.

------------------------------------------------------------------------

## 16. Documentation Before Implementation

Major subsystems should be designed before they are implemented.

The recommended workflow is:

``` text
       Idea
        │
        ▼
   Architecture
        │
        ▼
     Roadmap
        │
        ▼
 Design Documents
        │
        ▼
   Public API
        │
        ▼
  Implementation
        │
        ▼
    Validation
        │
        ▼
Documentation Review
        │
        ▼
  Stable Release
        │
        ▼
   Maintenance
```

This keeps implementation aligned with long-term architecture and
reduces costly redesigns.

------------------------------------------------------------------------

## Summary

These principles define the architectural foundation of the Betabox
platform.

They are intended to remain stable over time and guide decisions across
hardware abstraction, subsystem design, public APIs, services,
curriculum, and future platform development.
