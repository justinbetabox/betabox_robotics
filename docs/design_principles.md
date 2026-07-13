# Betabox Platform Design Principles

**Status:** Foundational Design Principles\
**Project:** Betabox Robot Platform

------------------------------------------------------------------------

## Purpose

This document defines the foundational principles that guide the design of the Betabox Platform.

Every public API, robot implementation, subsystem, platform service, and hardware abstraction should follow these principles.

When an implementation decision conflicts with these principles, the implementation should normally be reconsidered before the principles are changed.

These principles may evolve deliberately as the platform matures, but they should not be changed merely to accommodate an inconvenient implementation.

------------------------------------------------------------------------

## Student First

Public APIs should read naturally and be easy for beginners to understand.

Preferred beginner-facing code should express clear robot behavior:

```python
car.forward(50)
car.say("Hello")
distance = car.distance()
```

Intentionally exposed subsystem APIs may provide more detailed control:

```python
car.drive.forward(50)
car.audio.say("Hello")
car.vision.capture()
```

Students should think about robot behavior and physical concepts, not hardware implementation details.

The easiest API to teach should also be a supported, stable API rather than a temporary wrapper around the “real” interface.

------------------------------------------------------------------------

## Stable Public API

The public API is the long-term contract between the platform and user code.

Student notebooks, curriculum, applications, teacher tools, and web interfaces should continue working even as internal implementations evolve.

Internal modules may change freely when those changes do not alter documented public behavior.

Breaking public API changes should be:

-    Deliberate
-    Rare
-    Documented
-    Tested
-    Accompanied by a migration path when practical

Compatibility is a design responsibility, not an afterthought.

------------------------------------------------------------------------

## Robot Behavior over Hardware Behavior

The public API should describe what the robot should do rather than how individual hardware components operate.

Good examples include:

```python
car.forward(50)
car.steering.left(20)
car.say("Hello")
car.capture()
```

Avoid exposing implementation details such as:

-    GPIO pin numbers
-    PWM channels
-    ADC registers
-    Linux device paths
-    Camera driver objects
-    Speech engine commands
-    I²C transactions

Hardware-oriented APIs may exist within the hardware abstraction layer, but they should not be required for ordinary student programs.

------------------------------------------------------------------------

## Clear Robot Identity

The public API should make it clear what kind of robot the user is controlling.

Concrete robot classes may provide the most natural entry point:

```python
from betabox_robotics import BetaboxCar

car = BetaboxCar()
```

Future robot implementations may follow the same model:

```python
arm = BetaboxArm()
tank = BetaboxTank()
```

Generic platform code may use a robot factory when it should not depend on a specific robot type:

```python
from betabox_robotics import Robot

robot = Robot.default()
```

Concrete robot classes and generic factory interfaces may coexist. Neither construction style should force applications to depend on internal subsystem implementations.

------------------------------------------------------------------------

## Hardware Independence

User code should not depend on a particular board, operating system, hardware library, driver, or communication protocol.

Hardware may change.

Drivers may change.

Operating systems may change.

The documented public API should remain stable whenever practical.

Hardware-specific behavior belongs behind robot implementations, configuration, subsystems, and hardware abstractions.

------------------------------------------------------------------------

## Composition over Inheritance

with clear responsibilities.

Examples include:

-    A robot composes its major subsystems.
-    Drive composes motors and steering.
-    A motor uses PWM and direction control.
-    A servo uses a PWM interface.
-    Vision composes a frame source and frame consumers.
-    Sensors compose individual sensor components.

Inheritance may still be used when it represents a genuine shared abstraction, but it should not be used merely to reuse implementation code.

Prefer:

-    Explicitly composed components
-    Small interfaces
-    Delegation
-    Replaceable implementations

Avoid deep inheritance hierarchies that hide behavior or make resource ownership unclear.

------------------------------------------------------------------------

## Reusable Subsystems

Subsystem implementations should be reusable across multiple robot platforms whenever practical.

Robot-specific wiring, calibration, installed capabilities, and hardware selections belong in robot configuration or robot implementations rather than inside reusable subsystem modules.

Examples:

-    Drive should not know that it belongs to a Betabox Car.
-    Audio should not assume one specific speech engine.
-    Sensors should not assume fixed pin or channel assignments.
-    Vision should not depend on one application or streaming protocol.

Subsystems may receive configuration values and hardware dependencies during construction.

They should not import or depend directly on a concrete robot implementation or a robot-specific configuration module.

This separation allows new robot platforms to reuse existing subsystem implementations with minimal or no modification.

------------------------------------------------------------------------

## One-Way Dependency Direction

Dependencies should always flow from robot-specific implementations
toward reusable subsystem implementations.

```text
   Applications
        │
        ▼
 Public Robot API
        │
        ▼
Robot Implementations
        │
        ▼
Reusable Subsystems
        │
        ▼
Hardware Abstractions
        │
        ▼
Linux / Device Drivers
```

Platform services may support multiple internal layers, but they should not create upward dependencies or expose implementation details to application code.

The following rules apply:

-    Applications depend on public interfaces.
-    Robot implementations compose reusable subsystems.
-    Subsystems depend on supplied configuration and hardware abstractions.
-    Hardware abstractions depend on hardware libraries and operating-system interfaces.
-    Reusable subsystems do not depend on concrete robot implementations.
-    Hardware abstractions do not depend on robots or subsystems.
-    Internal modules do not depend on student applications.

------------------------------------------------------------------------

## Single Responsibility

Every class, module, subsystem, and service should have one clearly defined primary responsibility.

Responsibilities should not overlap unnecessarily.

A class should not simultaneously manage unrelated concerns such as:

-    Hardware communication
-    User-interface formatting
-    Configuration loading
-    Resource scheduling
-    Application policy

When a component becomes difficult to describe in one clear sentence, it may be responsible for too much.

Single responsibility should be applied pragmatically. It should improve clarity rather than produce excessive numbers of tiny classes with no independent purpose.

------------------------------------------------------------------------

## Stable Subsystem Boundaries

Each major subsystem should provide a clear and documented interface.

Current subsystems include:

-    Drive
-    Vision
-    Sensors
-    Audio
-    System

Subsystems should communicate through documented interfaces rather than reaching into one another’s private implementation details.

Subsystem boundaries should remain stable even when their internal components change.

A subsystem should expose enough functionality to be useful without leaking the hardware or service implementation beneath it.

------------------------------------------------------------------------

## Explicit and Predictable Behavior

The platform should not silently perform surprising actions or change unrelated hardware state.

Behavior should be:

-    Predictable
-    Documented
-    Observable
-    Consistent
-    Easy to reason about

Methods that change hardware state should make that effect clear through their names and documentation.

Validation behavior must also be explicit. Invalid inputs should be handled through a documented policy, such as:

-    Rejecting the value with a clear exception
-    Clamping the value to a documented safe range
-    Returning a documented status result

Silent coercion should be avoided when it could conceal a programming mistake.

------------------------------------------------------------------------

## Physical Units

Public APIs should use real-world units whenever practical.

Examples include:

-    Degrees
-    Percent speed
-    Centimeters
-    Volts
-    Seconds
-    Frames per second
-    Hertz

Students should not need to understand register values, pulse widths, raw ADC ranges, or timing calculations for ordinary use.

Units should be documented in method signatures, docstrings, examples, and validation rules.

A method should not return an unexplained numeric value whose unit must be inferred.

------------------------------------------------------------------------

## Hide Incidental Complexity

Implementation details should remain inside the platform unless exposing them provides clear educational or technical value.

Examples of incidental complexity include:

-    GPIO configuration
-    PWM timing
-    I²C retries
-    Camera drivers
-    Linux process management
-    Streaming protocols
-    File-system paths
-    Hardware calibration storage
-    Service startup order

Students should interact primarily with robot concepts.

Advanced interfaces may expose additional control intentionally, but low-level complexity should not leak accidentally through the primary API.

------------------------------------------------------------------------

## Explicit Configuration

Robot-specific differences should be represented through explicit configuration rather than hidden constants or scattered conditionals.

Configuration may define:

-    Pin and channel assignments
-    Motor reversal
-    Steering limits
-    Sensor calibration
-    Voltage thresholds
-    Camera defaults
-    Installed capabilities
-    Media locations

Configuration should be:

-    Validated
-    Typed where practical
-    Easy to inspect
-    Separate from reusable subsystem logic
-    Supplied explicitly during robot construction

Defaults should be safe and appropriate for the standard supported robot.

A reusable subsystem should not need to know which robot configuration file supplied its values.

------------------------------------------------------------------------

## Exclusive Resource Ownership

Hardware resources that cannot safely be shared should have one authoritative owner.

Examples include:

-    Camera
-    Drive motors
-    Steering servo
-    Audio output device
-    PWM channels
-    Sensor buses when exclusive access is required

Other components should access those resources through the owning subsystem or a platform-managed resource interface rather than opening competing hardware sessions.

Resource ownership should prevent:

-    Camera conflicts
-    Multiple components controlling the same motor
-    Overlapping audio playback without coordination
-    Conflicting PWM output
-    Unsafe concurrent hardware access

Ownership must remain clear even when multiple public methods provide access to the same underlying capability.

------------------------------------------------------------------------

## Predictable Lifecycle and Cleanup

Every resource-owning component should have a predictable lifecycle.

Components should clearly define how they:

-    Initialize
-    Start
-    Stop
-    Close
-    Release resources
-    Recover from partial startup
-    Handle repeated cleanup calls

Robot implementations should coordinate subsystem cleanup and leave hardware in a safe state.

The preferred bounded-use pattern should support context management:

```python
with BetaboxCar() as car:
    car.forward(50)
```

When the context exits, the robot should safely stop active behavior and release owned resources.

Cleanup should remain safe after an exception and should be idempotent wherever practical.

------------------------------------------------------------------------

## Safe by Default

The platform should choose the safest reasonable documented behavior.

Examples include:

-    Starting motors in a stopped state
-    Stopping drive hardware during cleanup
-    Preventing abrupt motor direction reversals
-    Enforcing documented steering limits
-    Releasing camera and audio resources
-    Recovering safely from partial initialization
-    Protecting shared resources from conflicting access
-    Rejecting unsafe or invalid configuration

Safety should not depend on students remembering an undocumented cleanup sequence.

Safe behavior must still remain explicit and documented. “Safe by default” should not become a justification for silently changing user intent.

------------------------------------------------------------------------

## Errors Should Be Clear

Errors should communicate what failed and what the user can do about it.

Public APIs should avoid unexplained sentinel values such as arbitrary negative numbers when a clearer exception, status object, or result type is practical.

Error handling should distinguish among failures such as:

-    Invalid user input
-    Missing hardware
-    Communication timeout
-    Resource conflict
-    Unsupported capability
-    Service failure

Hardware failures should not be hidden when doing so would leave the application with misleading data.

Where backward compatibility requires an older error behavior, the platform should document it and provide a path toward a clearer interface.

------------------------------------------------------------------------

## Test Every Layer

Every public component should include appropriate verification.

Depending on the component, this may include:

-    Documentation
-    Usage examples
-    Unit tests
-    Hardware validation
-    Subsystem validation
-    Robot validation
-    Integration tests

These forms of validation serve different purposes:

-    Unit tests verify isolated behavior and delegation.
-    Hardware validation verifies individual hardware abstractions or devices.
-    Subsystem validation verifies reusable subsystem APIs using configured robot hardware.
-    Robot validation verifies the fully composed robot platform.
-    Integration tests verify interactions among platform components and services.

A feature is not complete merely because it works once on one robot.

It should be possible to verify its expected behavior confidently and repeatably.

------------------------------------------------------------------------

## Documentation Before Implementation

Major capabilities and subsystems should be designed before substantial implementation begins.

The recommended workflow is:

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

Documentation-first design helps:

-    Establish responsibilities
-    Identify resource conflicts
-    Define stable public boundaries
-    Expose unclear naming
-    Reduce costly redesign
-    Keep implementation aligned with long-term architecture

Documentation should remain synchronized with implementation. A design document that no longer reflects supported behavior should be updated deliberately rather than allowed to drift.

------------------------------------------------------------------------

## Public APIs Must Be Deliberate

Not every useful internal method should become part of the public API.

A public method should provide a clear and supported capability.

Before expanding the public API, consider whether the functionality belongs in:

-    An existing top-level convenience method
-    A documented subsystem interface
-    An internal implementation class
-    A configuration option
-    A platform service
-    An advanced API

Public APIs should remain small enough to understand, document, test, and preserve.

Importability alone does not make a class or method public.

------------------------------------------------------------------------

## Compatibility Over Internal Convenience

Internal refactoring should not force unnecessary changes to curriculum or applications.

When practical, preserve compatibility through:

-    Delegation
-    Aliases
-    Stable method signatures
-    Consistent return types
-    Consistent physical units
-    Deprecation periods
-    Migration documentation

Implementation elegance is valuable, but it should not come at the cost of breaking supported user code without a compelling reason.

------------------------------------------------------------------------

## Summary

These principles define the architectural foundation of the Betabox Platform.

They guide decisions across:

-    Public APIs
-    Robot implementations
-    Reusable subsystems
-    Hardware abstractions
-    Configuration
-    Resource management
-    Platform services
-    Testing
-    Curriculum
-    Future application development

The platform should remain student-friendly at its surface, modular internally, explicit in its behavior, safe in its resource management, and stable as its implementation evolves.
