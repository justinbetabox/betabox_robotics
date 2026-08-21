# Platform Architecture

Betabox Robotics is a layered software platform for the Betabox robotic car.

The architecture separates physical hardware access, reusable robot subsystems,
robot composition, centralized runtime ownership, platform services, and
student-facing applications.

The primary goals are to provide a simple public API while ensuring that
multiple applications can safely share a single physical robot.

## Architecture Overview

```text
Applications
    │
    ├── Betabox Launchpad
    ├── Jupyter / student code
    ├── CLI and administration tools
    └── Platform services
            │
            ▼
       Public Robot API
            │
            ▼
     Central Robot Runtime
            │
            ├── Drive
            ├── Sensors
            ├── Camera Mount
            ├── Audio
            ├── Vision
            └── System
                    │
                    ▼
          Hardware Abstractions
                    │
                    ├── GPIO
                    ├── I2C
                    ├── ADC
                    ├── PWM
                    ├── Motors
                    └── Servos
```

Each layer has a distinct responsibility.

Applications should use the highest-level interface appropriate for their
purpose rather than reaching through layers to access hardware directly.

## Design Principles

### One Robot, One Hardware Owner

A Betabox contains one set of physical hardware.

GPIO devices, motors, servos, sensors, and other hardware must not be
independently constructed by every application that wants to use the robot.

The central robot runtime owns the robot hardware and coordinates access to it.

Launchpad, student programs, calibration tools, diagnostics, and platform
services communicate with the runtime rather than competing for the underlying
hardware.

### High-Level APIs First

Student programs and normal applications should use the public Robot API.

```python
from betabox_robotics import Robot

robot = Robot.default()
```

Applications that require lower-level platform functionality can use the
appropriate runtime or subsystem interface, but direct hardware access should
not be the normal application model.

### Reusable Layers

Hardware abstractions are not tied to one robot.

Subsystems compose hardware into reusable capabilities.

Robot implementations compose subsystems into a complete configured robot.

This keeps hardware-specific behavior, subsystem behavior, and application
behavior separate.

### Centralized Control

The runtime distinguishes between observing the robot and controlling its
actuators.

Read-only operations can be performed without acquiring exclusive robot
control when the runtime supports them.

Operations that control actuators use a control lease.

Only one control owner can hold that lease at a time.

This prevents Manual Drive, student code, calibration, and other applications
from issuing conflicting actuator commands.

### Safe Failure

Platform components should fail without leaving the robot in an unsafe state.

Examples include:

- stopping drive motors when control ends
- releasing runtime control leases
- validating actuator limits before issuing commands
- rejecting invalid calibration
- reporting unavailable hardware rather than silently assuming it works
- distinguishing observable hardware health from hardware that requires an
  active test

### Offline Classroom Operation

Normal classroom use must not depend on Internet access.

The robot provides its primary applications and services locally, including
Launchpad and JupyterHub.

Networking, deployment, and administrative features may use external network
access when available, but core robot operation is designed to remain local.

## Package Architecture

The main Python package is organized by platform responsibility.

```text
betabox_robotics/
├── audio/
├── calibration/
├── camera/
├── cli/
├── config/
├── curriculum/
├── drive/
├── hardware/
├── launchpad/
├── robots/
├── runtime/
├── sensors/
├── services/
├── system/
└── vision/
```

These packages fall into several architectural layers.

## Hardware Layer

The `hardware` package contains reusable abstractions for low-level physical
hardware.

Examples include:

- GPIO
- I2C
- ADC
- PWM
- motors
- servos

Hardware classes represent individual devices and communication mechanisms.
They should not contain Betabox application behavior.

For example, a motor abstraction knows how to control a motor. It does not
decide how a Betabox car should drive.

Robot-specific wiring and behavior belong in higher layers.

## Subsystem Layer

Subsystem packages compose low-level hardware into useful robot capabilities.

Current subsystem areas include:

- `drive`
- `sensors`
- `camera`
- `audio`
- `vision`
- `system`

### Drive

The drive subsystem combines the drive motors and steering hardware into a
coherent movement interface.

It is responsible for behavior such as:

- motor direction
- speed
- steering
- steering limits
- motor trim
- drive status

### Sensors

The sensor subsystem provides access to observable robot sensors, including:

- ultrasonic distance
- three-channel grayscale readings
- battery voltage and state

Sensor implementations translate raw hardware access into meaningful robot
data.

### Camera Mount

The camera mount provides pan and tilt control independently of the camera
image pipeline.

This distinction allows physical camera positioning and vision processing to
remain separate responsibilities.

### Audio

The audio subsystem provides robot audio capabilities such as:

- speech
- sound playback
- notes
- melodies
- playback state

### Vision

Vision provides camera and image-processing functionality including:

- frame capture
- snapshots
- recording
- streaming
- frame distribution
- metadata
- detection
- overlays

Normal platform camera ownership is coordinated through the vision service so
multiple applications do not independently open the camera.

### System

The system layer exposes information about the robot and host platform,
including:

- identity
- software version
- networking
- media paths
- status
- health information

Platform services build on this information for monitoring and diagnostics.

## Robot Layer

The `robots` package composes configured subsystems into complete robot
implementations.

The current concrete platform is the Betabox car.

Robot configuration describes how reusable hardware and subsystems are wired
and constrained for that robot.

This separation is important:

```text
Hardware abstraction
        ↓
Reusable subsystem
        ↓
Robot configuration and composition
        ↓
Public Robot API
```

Low-level hardware therefore does not need to know that it belongs to a
Betabox car.

## Public Robot API

The public Robot API is the normal programming interface for students and
applications.

```python
from betabox_robotics import Robot

robot = Robot.default()
```

`Robot.default()` returns the configured robot implementation for the current
platform.

The API provides convenient access to capabilities such as:

- movement
- steering
- sensors
- battery information
- audio
- vision
- system information

The public API deliberately hides most hardware ownership and platform
coordination details.

Student code should be able to express robot behavior without needing to know
how GPIO, I2C, runtime ownership, or platform services are implemented.

## Central Robot Runtime

The `runtime` package is the coordination boundary between applications and
the physical robot.

The runtime owns and initializes the robot hardware and keeps it available for
the lifetime of the runtime service.

Applications communicate with it through runtime clients.

Conceptually:

```text
Application A ─┐
Application B ─┼── Runtime Client ── Robot Runtime ── Physical Robot
Application C ─┘
```

This replaces the older model where each application independently
constructed the robot and attempted to own its hardware.

### Runtime Responsibilities

The runtime is responsible for:

- robot hardware initialization
- hardware lifetime
- runtime state
- actuator control
- control ownership
- sensor access
- calibration previews
- safe control release
- hardware shutdown

The runtime does not replace the reusable hardware and subsystem layers.

Instead, it owns their composed instances and provides coordinated access to
them.

## Control Ownership

Actuator operations require exclusive control.

An application requests a control lease from the runtime and identifies
itself as the control owner.

While the lease is active, other applications cannot independently acquire
actuator control.

For example:

```text
Manual Drive
     │
     ▼
Acquire control
     │
     ▼
Drive / steer
     │
     ▼
Release control
```

If Calibration attempts to acquire control during that period, the operation
is rejected as busy rather than competing with Manual Drive.

After Manual Drive releases control, Calibration can acquire its own lease.

This ownership model applies to applications rather than individual GPIO
devices.

## Read-Only Runtime Access

Not every operation requires exclusive control.

Supported read-only operations can query the runtime while another
application owns actuator control.

Examples include sensor readings and runtime status.

This is important for platform monitoring.

A student may be driving the robot while Launchpad continues displaying
battery and sensor information and the monitor continues observing hardware
health.

## Vision Architecture

Camera ownership differs slightly from normal actuator ownership because a
camera can produce one frame stream that is consumed by multiple clients.

The platform vision service owns normal camera operation.

Consumers use the shared service rather than opening independent camera
instances.

Conceptually:

```text
                   ┌── Launchpad
Camera ── Vision ──┼── Robot API
Service            ├── Snapshot
                   ├── Recording
                   └── Other consumers
```

This prevents camera conflicts while allowing multiple consumers to use the
same camera resource.

## Calibration Architecture

Calibration is split into three responsibilities.

```text
Calibration Models
        │
        ├── validation
        └── representation

Calibration Manager / Service
        │
        ├── persistence
        └── updates

Calibration Hardware
        │
        └── runtime-controlled previews and sampling
```

Calibration data includes:

- steering offset
- camera pan and tilt offsets
- motor trim
- grayscale floor and line references

Hardware calibration operations use the centralized runtime rather than
constructing independent motors or servos.

Calibration values are validated before they are persisted or applied.

For example, grayscale floor and line readings must have sufficient
separation on every sensor channel to prevent an unusable line calibration.

See [Calibration](calibration.md) for the detailed calibration model.

## Platform Services

The `services` package provides system-level functionality built around the
robot and host platform.

Responsibilities include:

- status collection
- platform health
- hardware checks
- diagnostics
- verification
- monitoring
- events
- boot announcements
- service management
- accounts and workspaces
- backup and recovery
- calibration services

Platform services should consume established robot, runtime, system, and
hardware-status interfaces rather than create competing ownership models.

## Monitoring and Health

The platform continuously observes state that can be checked safely while the
robot is running.

Examples include:

- runtime state
- Robot HAT communication
- battery state
- grayscale availability and plausibility
- ultrasonic availability
- camera and vision state
- system services
- CPU temperature
- memory
- disk usage
- undervoltage
- throttling
- networking

Meaningful state transitions are recorded as events.

Not all hardware can be passively verified.

A motor can be commanded successfully without proving that the physical motor
actually turned. The same limitation applies to servos and audible speaker
output.

The platform therefore distinguishes passive health monitoring from active
hardware validation.

See [Platform Health and Diagnostics](platform-health.md).

## Launchpad

The `launchpad` package is the primary browser application for the platform.

Launchpad uses platform APIs and services rather than implementing an
independent hardware stack.

Its responsibilities include presenting:

- Manual Drive
- Code / Jupyter access
- Vision
- Media
- Calibration
- Status
- Diagnostics
- Services
- Events
- Information
- user preferences

Manual Drive participates in runtime control ownership.

Calibration uses runtime-backed calibration hardware operations.

Status and diagnostics consume shared platform health information.

This keeps browser behavior aligned with the rest of the platform rather than
creating a second robot-control architecture.

See [Betabox Launchpad](launchpad.md).

## CLI and Administration

The `cli` package exposes platform administration through the `betabox`
command.

The CLI provides operations such as:

- status
- diagnostics
- services
- events
- logs
- monitoring
- restart and recovery operations
- platform information

CLI commands use the same underlying services as other platform interfaces
where practical.

The CLI is therefore an interface to the platform, not a separate
implementation of it.

## Configuration

Robot and platform configuration are kept separate from reusable
implementations.

Robot configuration describes hardware relationships and operating limits.

Platform configuration describes host-level settings such as:

- service definitions
- paths
- network settings
- monitoring configuration
- application configuration

Central configuration prevents individual services from accumulating
independent hard-coded assumptions about the deployed Betabox.

## Application Boundaries

When adding a new feature, choose the lowest appropriate existing layer.

A useful rule is:

```text
Does it talk directly to a physical device?
    → hardware

Does it combine hardware into a reusable capability?
    → subsystem

Does it describe or compose a complete robot?
    → robots

Does it coordinate shared access to the running robot?
    → runtime

Does it provide platform-level behavior or health?
    → services

Is it a browser interface?
    → launchpad

Is it a command-line interface?
    → cli
```

Features should not be placed in Launchpad or the CLI simply because that is
where they are first needed.

Reusable behavior belongs below the user-interface layer.

## Dependency Direction

Dependencies should generally flow downward through the architecture.

```text
Launchpad / CLI / Applications
              ↓
           Services
              ↓
       Robot API / Runtime
              ↓
            Robots
              ↓
          Subsystems
              ↓
           Hardware
```

Lower layers should not depend on Launchpad or other user interfaces.

Hardware abstractions should not contain classroom application behavior.

Subsystems should not know about web routes.

The runtime should coordinate the robot without depending on a particular
client application.

This dependency direction keeps the platform reusable and testable.

## Error Boundaries

Each layer translates failures into errors meaningful to its callers.

Examples include:

- hardware failures become hardware or subsystem errors
- runtime communication failures become runtime errors
- control conflicts become robot-busy errors
- service failures become service/status information
- HTTP interfaces translate application errors into appropriate responses

Errors should not be silently discarded when they affect platform state.

At the same time, expected failures should be represented at the appropriate
layer rather than leaking low-level implementation details all the way to the
student interface.

## Testing Boundaries

Testing follows the same architectural boundaries.

### Hardware validation

Verifies individual hardware abstractions against physical devices.

### Subsystem validation

Verifies reusable subsystem behavior using configured robot hardware.

### Runtime tests

Verify protocol behavior, clients, control ownership, and runtime
coordination.

### Service tests

Verify platform status, diagnostics, monitoring, calibration, and related
application behavior.

### Interface tests

Verify Launchpad and CLI behavior without redefining the underlying platform
logic.

Automated tests cannot prove all physical behavior, so hardware-affecting
changes also require appropriate real-robot validation.

## Current Scope

The current concrete robot implementation is the Betabox robotic car.

The architecture intentionally separates reusable platform components from
that concrete robot so additional robot implementations can reuse common
hardware, subsystem, runtime, service, and application infrastructure in the
future.

Future support does not require making current APIs generic without a concrete
need. The current Betabox car remains the reference implementation for the
platform.

## Related Documentation

- [Central Robot Runtime](runtime.md)
- [Betabox Launchpad](launchpad.md)
- [Installation](installation.md)
- [Development](development.md)
- [Calibration](calibration.md)
- [Platform Health and Diagnostics](platform-health.md)
- [Hardware](hardware.md)
