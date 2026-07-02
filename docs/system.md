# Betabox System Architecture

**Status:** Foundation  
**Project:** Betabox Robot Platform

------------------------------------------------------------------------

## Purpose

The System subsystem provides information about the robot platform and
shared system resources.

It exposes platform information through a stable public API while hiding
operating system implementation details.

------------------------------------------------------------------------

## Robot Composition

The System subsystem is a reusable subsystem implementation.

Robot implementations provide any platform-specific configuration
required to initialize the System subsystem.

Applications should normally access system information through:

```python
from betabox_car import Robot

robot = Robot()

status = robot.system.status()
```

The System subsystem should not depend on robot-specific configuration
internally.

Constructing the System subsystem directly remains appropriate for
validation, testing, and advanced configuration.

------------------------------------------------------------------------

## Responsibilities

The System subsystem is responsible for:

### Identity

-    Robot hostname
-    Platform version
-    Robot identity

### Network

-    IP addresses
-    Future network status

### Storage

-    Shared media directories
-    Platform file locations

### Platform Status

-    Status reporting
-    Health reporting

### Lifecycle

-    Shared initialization
-    Shared shutdown

------------------------------------------------------------------------

## Non-Responsibilities

The System subsystem is **not** responsible for:

-    Robot movement
-    Sensor acquisition
-    Vision processing
-    Camera control
-    Audio playback
-    Hardware control

The System subsystem reports platform information.

Other subsystems perform robot behavior.

------------------------------------------------------------------------

## Public API

```python
status = robot.system.status()

print(status.hostname)
print(status.ip_addresses)

health = robot.system.health()

paths = robot.system.media_paths()

print(paths.pictures)
print(paths.videos)
print(paths.sounds)

robot.system.ensure_media_paths()

robot.system.stop_all()
```

------------------------------------------------------------------------

## Internal Architecture

```text
System
 ├── Identity
 ├── Network
 ├── Storage
 ├── Health
 └── Lifecycle
```

------------------------------------------------------------------------

## Resource Ownership

The System subsystem owns shared platform resources.

The System subsystem owns:

-    Platform identity
-    Shared media directories
-    Platform status
-    Platform health
-    Shared platform resources

The System subsystem does not own motors, sensors, cameras, or audio
devices.

Instead, it coordinates platform-level information while other
subsystems own physical hardware.

------------------------------------------------------------------------

## Interaction with Other Subsystems

Applications access platform information through the Robot API.

The System subsystem provides platform information and lifecycle
services to higher-level software.

The System subsystem does not directly control Drive, Vision, Sensors,
or Audio.

```text
  Applications
        │
        ▼
     Robot API
        │
        ▼
      System
        │
        ▼
Platform Information
```

------------------------------------------------------------------------

## Future Expansion

Future capabilities may include:

-    Platform health aggregation
-    Network monitoring
-    Storage monitoring
-    Service monitoring
-    Diagnostics
-    Robot lifecycle management
-    Robot identity management
-    Service status reporting

------------------------------------------------------------------------

## Design Principles

The System subsystem follows the Betabox Platform Design Principles:

-    Stable Public API
-    Reusable Subsystems
-    Hardware Independence
-    Single Responsibility
-    Exclusive Resource Ownership
-    Safe by Default
-    Test Everything

------------------------------------------------------------------------

## Summary

The System subsystem provides a stable interface to the robot's operating
environment.

It owns platform-level resources such as identity, storage, networking,
and health information while remaining independent of robot-specific
implementations.

Applications interact with the platform through a stable System API,
allowing the underlying operating system and platform services to evolve
without affecting user code.
