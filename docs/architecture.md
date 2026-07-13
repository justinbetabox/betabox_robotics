# Betabox Platform Architecture

**Status:** Stable Architecture Specification\
**Project:** Betabox Robot Platform\
**Document:** `architecture.md`

------------------------------------------------------------------------

## Philosophy

The Betabox Platform is designed around a stable public Robot API that is independent of the underlying hardware implementation.

Applications, curriculum, notebooks, teacher tools, and web interfaces interact with robots through the Betabox Robot API. They should not depend directly on hardware libraries, Linux device interfaces, operating-system services, or implementation-specific modules.

The architecture separates stable user-facing interfaces from replaceable implementation details. Internal modules may evolve as hardware, operating systems, communication protocols, and technologies change while preserving the public Robot API wherever practical.

------------------------------------------------------------------------

## Architecture

``` text
           Applications
                │
                ▼
        Betabox Robot API
                │
                ▼
      Robot Implementations
     (Car and future robots)
                │
                ▼
       Reusable Subsystems
 ┌────────┬───────┬────────┬──────┐
 │        │       │        │      │
Drive   Vision  Sensors  Audio  System
                │
                ▼
        Platform Services
                │
                ▼
     Hardware Abstractions
                │
                ▼
     Linux / Device Drivers
```

Dependencies generally flow downward from stable, user-facing layers toward replaceable implementation layers.

Platform services may support multiple internal layers, but they remain hidden from normal student-facing code.

------------------------------------------------------------------------

## Design Goals

-    Stable public API
-    Backend-independent implementations
-    Composition over inheritance
-    Clear responsibility boundaries
-    Student-friendly programming interfaces
-    Physical concepts instead of hardware registers
-    Explicit behavior instead of implicit behavior
-    Exclusive ownership of shared hardware resources
-    Modular and reusable subsystem design
-    Straightforward extensibility
-    Robot-independent subsystem implementations
-    Predictable lifecycle and cleanup behavior
-    Compatibility across internal platform evolution

------------------------------------------------------------------------

## Architectural Layers

### Applications

Applications include:

-    Student notebooks
-    Curriculum
-    Teacher tools
-    Betabox Portal
-    Betabox Launchpad
-    Internal Betabox applications

Applications interact with robots through the public Robot API.

Applications may use top-level convenience methods such as:

```python
robot.forward(50)
robot.say("Hello")
distance = robot.distance()
```

They may also use intentionally exposed subsystem APIs when more detailed control is appropriate:

```python
robot.drive.forward(50)
robot.audio.say("Hello")
```

Applications should not import private implementation modules or communicate directly with hardware.

### Robot API

The Robot API is the stable programming interface presented to users and applications.

Responsibilities include:

-    Providing a consistent programming model
-    Coordinating subsystem access
-    Exposing student-friendly convenience methods
-    Exposing intentionally public subsystem interfaces
-    Managing robot lifecycle
-    Coordinating cleanup and resource release
-    Hiding implementation details
-    Preserving compatibility across platform evolution

The primary construction interface is the Robot factory:

```python
from betabox_robotics import Robot

robot = Robot.default()
```

Configured robots may also be constructed through an explicit configuration interface:

```python
robot = Robot.from_config(robot_config)
```

The concrete robot type returned by the factory may vary, but application code should normally depend on the public Robot API rather than the concrete implementation class.

### Robot Implementations

A robot implementation composes reusable subsystems into a complete physical robot.

The current primary implementation is:

-    Betabox Car

Potential future implementations include:

-    Betabox Arm
-    Betabox Tank
-    Betabox Drone

Robot implementations are responsible for:

-    Selecting subsystem implementations
-    Applying robot-specific configuration
-    Defining installed capabilities
-    Connecting public Robot API methods to composed subsystems
-    Coordinating startup and shutdown
-    Enforcing resource ownership across the complete robot

Robot-specific wiring, calibration, channel assignments, and hardware choices belong in robot configuration rather than in reusable subsystem modules.

Applications should normally construct a complete robot implementation, such as BetaboxCar, or use the generic Robot factory rather than constructing individual subsystem implementations.

### Reusable Subsystems

The platform is organized into major reusable subsystems:

-    Drive
-    Vision
-    Sensors
-    Audio
-    System

Each subsystem owns one area of robot functionality and should be reusable across multiple robot implementations whenever practical.

Subsystems may depend on abstract hardware interfaces and configuration values supplied during construction. They should not import or depend on a specific robot implementation or robot-specific configuration module.

For example:

-    Drive controls movement and steering.
-    Vision manages camera frames, snapshots, recording, and streaming.
-    Sensors expose measurements and interpreted sensor state.
-    Audio manages speech, sound playback, tones, and audio hardware.
-    System exposes platform identity, media paths, and operating-system information.

### Platform Services

Platform services provide shared internal capabilities used by robot implementations and subsystems.

Examples include:

-    Resource management
-    Configuration loading and validation
-    Robot lifecycle coordination
-    Event distribution
-    Background service integration
-    Logging
-    Monitoring
-    Future scheduling

Platform services coordinate shared behavior while remaining invisible to ordinary student-facing code.

They should not unnecessarily expose Linux services, process management, file-system details, or internal communication mechanisms through the public Robot API.

### Hardware Abstractions

The hardware layer isolates higher layers from hardware libraries and operating-system interfaces.

It contains low-level interfaces and device abstractions for capabilities including:

-   GPIO
-   PWM
-   I²C
-   ADC
-   Motors
-   Servos
-   Hardware sensors
-   Future hardware peripherals

Hardware abstractions translate low-level implementation details into clear Python interfaces.

Higher layers should not communicate directly with Linux device files, GPIO libraries, I²C registers, or hardware-specific driver APIs when an appropriate Betabox abstraction exists.

------------------------------------------------------------------------

## Configuration

Configuration defines how reusable implementations are assembled for a particular robot.

Configuration may include:

-    Pin assignments
-    PWM channels
-    ADC channels
-    Motor direction
-    Reversal flags
-    Steering limits
-    Calibration values
-    Voltage thresholds
-    Camera defaults
-    Installed capabilities

Reusable subsystem modules should accept configuration through explicit construction or factory methods.

They should not import a specific robot configuration directly.

Robot implementations are responsible for choosing and supplying the appropriate configuration.

------------------------------------------------------------------------

## Resource Ownership

Each subsystem owns the hardware resources it manages.

Examples include:

-    Vision owns the camera and active frame source.
-    Drive owns motors and steering hardware.
-    Audio owns audio playback and amplifier control.
-    Sensor components own their underlying sensor devices.
-    System coordinates platform-level operating-system capabilities.

Resources that cannot safely be shared concurrently must have one authoritative owner.

Shared access is coordinated internally by the platform rather than by user code. Applications should not open competing camera sessions, independently control the same PWM channel, or directly manipulate hardware already owned by a subsystem.

Resource ownership should provide:

-    Deterministic startup
-    Conflict prevention
-    Predictable shutdown
-    Safe cleanup after errors
-    Clear responsibility for hardware state

------------------------------------------------------------------------

## Lifecycle

Robot implementations and resource-owning subsystems must support predictable lifecycle management.

A robot may be used directly:

```python
robot = Robot.default()

try:
    robot.forward(50)
finally:
    robot.close()
```

The preferred form for bounded programs is a context manager:

```python
with Robot.default() as robot:
    robot.forward(50)
```

Lifecycle management should:

-    Stop moving hardware when appropriate
-    Release the camera
-    Stop active recordings and streams
-    Stop audio playback
-    Release GPIO, PWM, I²C, and other device resources
-    Leave the robot in a safe state
-    Remain safe when cleanup is called more than once

------------------------------------------------------------------------

## Extensibility

New capabilities should extend existing subsystem boundaries whenever practical.

Examples include:

-    New sensors belong in the Sensors subsystem.
-    New detectors and frame consumers belong in the Vision subsystem.
-    New speech or playback engines belong in the Audio subsystem.
-    New drive hardware belongs behind Drive abstractions.
-    New hardware devices remain behind hardware abstractions whenever possible.

A new top-level Robot API method should be added only when it provides a clear, broadly useful, student-friendly capability.

Implementation growth should not automatically expand the public API.

This approach minimizes changes to curriculum and student code while allowing the platform to evolve internally.

------------------------------------------------------------------------

## Dependency Direction

The primary dependency direction is:

    Applications
         │
         ▼
     Robot API
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

Platform services support internal coordination across these layers without becoming direct dependencies of application code.

The following rules apply:

-    Applications depend on the public Robot API.
-    The Robot API is implemented by robot implementations.
-    Robot implementations compose reusable subsystems.
-    Reusable subsystems depend on configuration values and hardware abstractions.
-    Hardware abstractions depend on hardware libraries and operating-system interfaces.
-    Reusable subsystems never depend on a concrete robot implementation.
-    Hardware abstractions never depend on subsystems or robots.
-    Internal implementation modules should not import application code.

These dependency rules allow new robot platforms and hardware backends to reuse existing components without modifying application code.

------------------------------------------------------------------------

## Public and Internal Interfaces

Not every importable class is part of the stable public API.

Public interfaces are explicitly exported and documented.

Internal interfaces may change as the implementation evolves.

Applications should depend only on:

-    Classes and functions exported by supported public package entry points
-    Methods documented in api.md
-    Documented subsystem interfaces
-    Supported configuration interfaces

Modules, attributes, or classes marked private or omitted from public documentation should be treated as implementation details.

------------------------------------------------------------------------

## Long-Term Goal

The Betabox Robot API and reusable subsystem architecture are intended to become the stable foundation for all Betabox robotic platforms.

Applications, curriculum, notebooks, teacher tools, Launchpad, and Portal interfaces should continue to function even as hardware implementations, operating systems, communication protocols, and internal technologies evolve.

The platform should allow internal components to be replaced, extended, or independently tested without requiring unnecessary changes to user-facing software.

------------------------------------------------------------------------

## Architectural Principles

-    Applications interact through the public Robot API.
-    Robot implementations compose reusable subsystems.
-    Reusable subsystems do not depend on concrete robot implementations.
-    Robot-specific wiring and calibration belong in configuration.
-    Hardware remains behind hardware abstractions.
-    Shared hardware has one authoritative owner.
-    Public interfaces remain small, explicit, and stable.
-    Internal implementations may evolve without unnecessarily affecting application code.
-    Lifecycle management leaves hardware in a safe and predictable state.

------------------------------------------------------------------------

## Summary

The Betabox Platform is organized into clear layers with explicit responsibilities and one-way dependency boundaries.

A stable Robot API separates user-facing software from robot implementations, reusable subsystems, hardware abstractions, and operating-system details.

This structure allows the platform to evolve while preserving compatibility, resource safety, maintainability, testability, and a consistent programming experience across Betabox robotic platforms.
