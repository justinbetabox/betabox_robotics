# Betabox System Subsystem

**Status:** Subsystem Design Specification\
**Project:** Betabox Robot Platform\
**Document:** `system.md`

------------------------------------------------------------------------

## Purpose

The System subsystem provides a stable, reusable interface for platform
identity, status, health, networking, storage, and shared
operating-environment information.

It presents a simple, platform-independent API while hiding
operating-system implementation details.

Student code should describe **what platform information it needs**, not
how Linux, networking, or file-system resources are implemented.

------------------------------------------------------------------------

## Robot Composition

The System subsystem is a reusable subsystem implementation composed
into a robot implementation.

Robot implementations provide the configuration required to construct
the System subsystem, including media locations, platform identity, and
operating-system integration.

Applications should normally access system information through the Robot
API:

``` python
from betabox_robotics import BetaboxCar

with BetaboxCar() as car:
    print(car.hostname())
    print(car.health())
```

The System subsystem remains available for more detailed access:

``` python
car.system.hostname()
car.system.status()
car.system.health()
```

Constructing the System subsystem directly is generally reserved for
hardware validation, subsystem validation, testing, and advanced
applications.

------------------------------------------------------------------------

## Responsibilities

### Identity

-    Robot hostname
-    Robot identity
-    Platform version

### Network

-    IP addresses
-    Network information

### Storage

-    Shared media directories
-    Platform file locations

### Platform Information

-    Status reporting
-    Health reporting
-    Version reporting

### Lifecycle Support

-    Shared initialization
-    Shared cleanup
-    Platform preparation

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

### Robot API

``` python
car.hostname()
car.ip_addresses()

car.media_paths()
car.ensure_media_paths()

car.status()
car.health()
```

### System Subsystem API

``` python
car.system.hostname()
car.system.ip_addresses()

car.system.media_paths()
car.system.ensure_media_paths()

car.system.status()
car.system.health()
```

------------------------------------------------------------------------

## Internal Architecture

``` text
System
 ├── Identity
 ├── Network
 ├── Storage
 ├── Status
 ├── Health
 └── Lifecycle
```

The System subsystem aggregates platform information while hiding
operating-system implementation details.

------------------------------------------------------------------------

## Resource Ownership

The System subsystem owns platform-level services related to:

-    Status aggregation
-    Health aggregation
-    Shared media directory management
-    Platform information interfaces

The System subsystem does not own motors, sensors, cameras, or audio
devices.

Robot implementations coordinate hardware-owning subsystems
independently.

------------------------------------------------------------------------

## Behavior Guarantees

The System subsystem should provide predictable behavior.

Expected guarantees include:

-    Platform information is read-only.
-    Status and health information are reported consistently.
-    Media directories are created when requested.
-    Operating-system details remain hidden.
-    Public APIs remain platform independent.

------------------------------------------------------------------------

## Interaction with Other Subsystems

``` text
    Robot API
        │
        ▼
      System
        │
        ▼
Platform Information
```

The System subsystem provides shared platform information to
higher-level software.

It does not directly control Drive, Vision, Sensors, or Audio.

------------------------------------------------------------------------

## Implementation Details

The public API intentionally hides implementation details such as:

-    Linux commands
-    Network interfaces
-    File-system layout
-    Operating-system services
-    Platform-specific utilities

These implementation details may evolve while the public API remains
stable.

------------------------------------------------------------------------

## Future Expansion

Future capabilities may include:

-    Platform health aggregation
-    Network monitoring
-    Storage monitoring
-    Service monitoring
-    Diagnostics
-    Software version reporting
-    Configuration inspection
-    Resource utilization

Future capabilities should extend the existing API without requiring
changes to student applications.

------------------------------------------------------------------------

## Testing and Validation

The System subsystem should be verified through:

-    Unit tests
-    Hardware validation
-    Subsystem validation
-    Robot validation

Subsystem validation verifies the reusable System subsystem using a
configured robot implementation.

Robot validation verifies complete platform information through the
Robot API.

------------------------------------------------------------------------

## Design Principles

The System subsystem follows the Betabox Platform Design Principles:

-    Student First
-    Stable Public API
-    Reusable Subsystems
-    Hardware Independence
-    Single Responsibility
-    Explicit Behavior
-    Safe by Default
-    Test Everything

------------------------------------------------------------------------

## Summary

The System subsystem provides a stable, reusable interface to the
robot's operating environment.

It exposes platform identity, networking, storage, status, and health
information through a consistent Robot API while hiding operating-system
implementation details.

Higher-level software uses this information to understand the robot
platform without depending on Linux-specific behavior.
