# Betabox Platform Architecture

**Status:** Stable Architecture Specification\
**Project:** Betabox Robot Platform\
**Document:** `architecture.md`

------------------------------------------------------------------------

## Philosophy

The Betabox Platform is designed around a stable public Robot API that
is independent of the underlying hardware implementation.

Applications, curriculum, notebooks, teacher tools, and future web
interfaces interact exclusively with the Betabox Robot API. They should
never depend directly on hardware libraries, Linux interfaces, or
implementation-specific modules.

The architecture separates stable user-facing interfaces from
replaceable implementation details. Internal modules may evolve as
hardware, operating systems, and technologies change while preserving
the public Robot API.

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
     (Car, Arm, Tank, Drone)
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

Each layer communicates only with the layer immediately below it.

------------------------------------------------------------------------

## Design Goals

-    Stable public API
-    Backend-independent implementation
-    Composition over inheritance
-    One responsibility per class
-    Student-friendly programming interface
-    Physical concepts over hardware registers
-    Explicit behavior over implicit behavior
-    Exclusive ownership of shared hardware resources
-    Modular subsystem design
-    Straightforward extensibility
-    Robot-independent subsystem implementations

------------------------------------------------------------------------

## Architectural Layers

### Applications

Applications include:

-    Student notebooks
-    Curriculum
-    Teacher tools
-    Future Betabox Portal
-    Internal Betabox applications

Applications interact with the robot exclusively through the Robot API.

### Robot API

The Robot API is the stable programming interface presented to users.

Responsibilities include:

-    Coordinating subsystem access
-    Providing a consistent programming model
-    Hiding implementation details
-    Remaining stable across platform evolution

### Robot Implementations

Each physical robot platform composes reusable subsystem
implementations into a complete robot.

Examples include:

-    Betabox Car
-    Betabox Arm
-    Betabox Tank
-    Betabox Drone

Robot implementations provide platform-specific configuration while
reusing common subsystem implementations whenever practical.

Applications should normally construct a Robot rather than individual subsystem implementations.

### Reusable Subsystems

The platform is organized into major subsystems:

-    Drive
-    Vision
-    Sensors
-    Audio
-    System

Each subsystem owns a single area of robot functionality and is designed
to be reusable across multiple robot implementations.

Subsystems should not depend on robot-specific configuration.

### Platform Services

Platform services provide shared capabilities used across multiple
subsystems.

Examples include:

-    Resource management
-    Configuration
-    Robot lifecycle
-    Event distribution
-    Background services
-    Future scheduling and monitoring

These services coordinate platform behavior while remaining invisible to
student-facing code.

### Hardware Abstractions

The hardware layer provides low-level interfaces for physical devices
including:

-   GPIO
-   PWM
-   I²C
-   ADC
-   Motors
-   Servos
-   Sensors
-   Future hardware peripherals

Higher layers should never communicate directly with Linux hardware interfaces.

------------------------------------------------------------------------

## Resource Ownership

Each subsystem owns the hardware resources it manages.

Examples:

-   Vision owns the camera.
-   Drive owns motors and steering.
-   Audio owns audio hardware.
-   Sensor components own their sensor devices.
-   System manages platform services.

Shared resources are coordinated internally by the platform rather than
by user code.

------------------------------------------------------------------------

## Extensibility

New robot capabilities should extend existing subsystem interfaces
whenever practical.

Examples:

-   New sensors belong in the Sensors subsystem.
-   New detectors belong in the Vision subsystem.
-   New audio features belong in the Audio subsystem.
-   New hardware should remain behind existing abstractions whenever
    possible.

This approach minimizes changes to student-facing APIs while allowing
the platform to evolve internally.

------------------------------------------------------------------------

## Dependency Direction

Dependencies flow from robot-specific implementations toward reusable
subsystems.

Reusable subsystem implementations should not depend on robot-specific
configuration.

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

This allows new robot platforms to reuse existing subsystem
implementations without modification.

------------------------------------------------------------------------

## Long-Term Goal

The Betabox Robot API, together with reusable subsystem implementations, is intended to become the stable foundation for all Betabox robotic platforms.

Applications, curriculum, notebooks, teacher tools, and future web
interfaces should continue to function even as hardware implementations,
operating systems, communication protocols, and internal implementations
evolve.

The platform architecture is designed so that internal components can be
replaced or expanded without requiring changes to user-facing software.

------------------------------------------------------------------------

## Architectural Principles

-    Layers communicate only with the layer below.
-    Robot implementations compose reusable subsystems.
-    Reusable subsystems never depend on robot implementations.
-    Applications interact exclusively through the Robot API.

------------------------------------------------------------------------

## Summary

The Betabox Platform is organized into clear architectural layers with
well-defined responsibilities.

A stable Robot API separates user-facing software from implementation
details, allowing the platform to evolve while preserving compatibility,
maintainability, and a consistent programming experience.
