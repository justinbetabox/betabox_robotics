# Central Robot Runtime

The Betabox Robot Runtime is the centralized owner and coordinator of the
physical robot hardware.

It allows Launchpad, student programs, calibration tools, monitoring, and
other platform applications to safely share one running robot without
independently constructing or competing for the same hardware.

The runtime is the normal application boundary for access to drive hardware,
sensors, and the camera mount.

## Purpose

A Betabox contains one physical set of robot hardware.

Without centralized ownership, multiple processes could independently attempt
to initialize or control:

- motors
- steering
- camera servos
- ADC channels
- ultrasonic hardware
- other Robot HAT resources

That creates several problems:

- competing GPIO ownership
- conflicting actuator commands
- hardware initialization conflicts
- one application disrupting another
- cleanup in one process affecting another
- unreliable status and diagnostics

The runtime solves these problems by keeping the composed robot hardware in
one long-lived process and exposing controlled access to applications through
runtime clients.

Conceptually:

```text
Launchpad ─────────────┐
Jupyter / student code ├── RobotRuntimeClient ── Robot Runtime ── Robot Hardware
Calibration ───────────┤
Platform services ─────┘
```

Applications no longer need to own the underlying robot hardware themselves.

## Responsibilities

The runtime is responsible for:

- initializing robot hardware
- maintaining hardware for the runtime lifetime
- exposing robot state
- coordinating actuator ownership
- issuing drive commands
- controlling steering
- controlling the camera mount
- providing sensor readings
- supporting calibration previews
- safely releasing control
- safely shutting down hardware

The runtime is not intended to replace the hardware, subsystem, or robot
layers.

Instead, it owns the configured instances created from those layers.

```text
Robot Runtime
     │
     ▼
Configured Robot
     │
     ├── Drive
     ├── Sensors
     └── Camera Mount
             │
             ▼
          Hardware
```

## Runtime Package

Runtime functionality lives in:

```text
betabox_robotics/runtime/
```

The package contains the runtime server, client, protocol, control-management,
sensor interfaces, and supporting runtime state and error handling.

Applications should normally use the public runtime client rather than
depending on runtime implementation internals.

## Runtime Lifecycle

The runtime has a distinct lifecycle.

Conceptually:

```text
Process starts
     ↓
Runtime created
     ↓
Robot ownership established
     ↓
Hardware initialized
     ↓
Runtime ready
     ↓
Serve clients
     ↓
Shutdown requested
     ↓
Control released
     ↓
Actuators made safe
     ↓
Hardware closed
```

Hardware initialization happens once for the runtime rather than once for
every application.

This is a fundamental property of the centralized runtime architecture.

## Runtime State

The runtime exposes state describing whether it is ready to serve robot
operations.

Platform status and diagnostics use runtime state to distinguish problems such
as:

- runtime service unavailable
- runtime starting
- hardware ownership unavailable
- hardware initialization failure
- runtime ready

Runtime availability and physical hardware health are related but are not the
same thing.

A running runtime process does not automatically prove that every attached
physical component is functioning.

## Runtime Client

Applications communicate with the runtime through `RobotRuntimeClient`.

```python
from betabox_robotics.runtime.client import RobotRuntimeClient

client = RobotRuntimeClient()
```

The client provides the application-facing runtime operations and hides the
underlying transport and protocol details.

Applications should use the client rather than opening the runtime transport
directly.

A client object does not itself mean that the application owns robot control.

Control is acquired separately when required.

## Read-Only Operations

Supported read-only operations do not require an exclusive control lease.

This allows applications to observe the robot while another application is
actively controlling it.

Examples include operations such as:

- runtime status
- battery information
- grayscale readings
- ultrasonic readings

Conceptually:

```text
Student program
     │
     └── owns actuator control

Launchpad Status ──────┐
Monitor ───────────────┼── read sensor/runtime state concurrently
Diagnostics ───────────┘
```

This distinction is important for the platform health system.

Status monitoring should not have to take robot control merely to determine
whether a sensor is available.

## Actuator Control

Operations that can physically control the robot require a control lease.

This includes operations involving:

- drive motors
- steering
- camera mount movement
- calibration actuator previews

An application acquires control before issuing these commands.

For example:

```python
from betabox_robotics.runtime.client import RobotRuntimeClient

client = RobotRuntimeClient()

with client.control("Example Application") as control:
    client.drive_forward(
        control.token,
        50.0,
    )

    client.drive_stop(
        control.token,
    )
```

The control token identifies the active lease and must be supplied to
operations requiring actuator control.

Applications should normally use the control context manager so the lease is
released even when an operation fails.

## Control Ownership

Only one application can own actuator control at a time.

Each lease includes an owner name describing the application currently using
the robot.

Examples include:

```text
Launchpad Manual Drive
Launchpad Steering Calibration
Launchpad Camera Calibration
Launchpad Motor Calibration
Launchpad Calibration Reset
Student Program
```

The owner is useful for both conflict reporting and platform status.

Conceptually:

```text
                Robot Runtime
                     │
              Control available
                     │
          ┌──────────┴──────────┐
          │                     │
    Manual Drive          Calibration
       requests             requests
       control              control
          │
          ▼
     lease granted
          │
          └──────── Calibration rejected as busy
```

After Manual Drive releases its lease, Calibration can acquire a new one.

## Control Tokens

A successful control acquisition produces a token.

Actuator operations require that token.

The runtime validates that the token belongs to the currently active control
lease before performing the requested operation.

This prevents a client from issuing actuator commands merely because it can
connect to the runtime.

A token from an expired or released lease is not valid control authorization.

## Control Release

Control must always be released when an application is finished.

The preferred pattern is:

```python
with client.control("My Application") as control:
    # controlled operations
    ...
```

The context manager ensures release during normal completion and exception
handling.

Control release is also a safety boundary.

Applications should not leave drive motors running merely because a client
disconnects or a control operation terminates.

The runtime's control lifecycle is responsible for returning controlled
hardware to an appropriate safe state.

## Manual Drive

Launchpad Manual Drive is a runtime control client.

When a browser establishes Manual Drive control:

```text
Browser
    ↓
Launchpad Manual Drive
    ↓
RobotRuntimeClient
    ↓
Acquire control lease
    ↓
Drive / steering commands
```

The lease remains associated with Manual Drive while that control session is
active.

If another application already owns the robot, Manual Drive cannot silently
take control away from it.

Likewise, calibration cannot take control while Manual Drive owns the lease.

## Student Code

The public Robot API uses the centralized runtime for normal robot operations.

This allows student programs to use a simple high-level API without needing
to understand runtime transport, ownership implementation, or physical GPIO
resources.

For example:

```python
from betabox_robotics import Robot

robot = Robot.default()
```

The high-level interface remains the preferred student API.

The runtime is infrastructure supporting that API, not a replacement API that
students are expected to use directly for ordinary lessons.

## Sensor Access

Runtime sensor interfaces expose sensor data from the runtime-owned robot.

Current observable robot sensors include:

- battery
- grayscale
- ultrasonic

Sensor reads are designed to coexist with actuator ownership.

For example, while Manual Drive owns control:

```text
Manual Drive ── control lease ── drive / steering

Status ───────────────────────── battery
Monitor ──────────────────────── ultrasonic
Launchpad ────────────────────── grayscale
```

The applications do not construct competing sensor hardware to obtain those
values.

## Hardware Monitoring

The runtime provides the platform with access to observable robot state, but
it does not claim to prove that every physical device works.

For example:

- an ultrasonic sensor can be read and its availability observed
- grayscale values can be read and checked for plausibility
- battery voltage can be observed

By contrast:

- a motor command cannot prove that the physical motor turned
- a steering command cannot prove that the wheels moved
- a camera-servo command cannot prove the mount physically moved

The platform health system therefore combines runtime information with
appropriate passive hardware checks rather than treating runtime readiness as
proof of complete physical health.

## Calibration

Calibration actuator operations run through the runtime.

The calibration hardware layer uses `RobotRuntimeClient` rather than
constructing independent motors or servos.

This allows calibration to participate in the same control ownership model as
other applications.

### Steering Preview

A steering calibration preview:

1. acquires runtime control;
2. temporarily applies the candidate steering offset;
3. centers the steering using that offset;
4. restores the runtime's previous calibration state;
5. releases control.

This allows a user to physically preview a calibration value before saving it.

### Camera Mount Preview

Camera calibration follows the same pattern for pan and tilt offsets.

The candidate offsets are applied for the physical preview and the runtime's
previous calibration state is restored afterward.

### Motor Trim Preview

Motor calibration uses runtime-controlled drive hardware to preview candidate
motor trim values.

Because this operation physically drives the robot, it requires exclusive
control.

### Calibration Reset

A full Launchpad calibration reset also uses runtime control.

The reset operation:

1. acquires control;
2. stops the motors;
3. returns steering to its uncalibrated physical center;
4. returns camera pan and tilt to their uncalibrated physical centers;
5. releases runtime control;
6. resets the persisted calibration to defaults.

The physical reset occurs before persisted calibration is removed.

If another application owns the robot, the reset is rejected as busy rather
than resetting persisted values without being able to safely reposition the
hardware.

See [Calibration](calibration.md) for calibration persistence and validation.

## Vision and the Runtime

Vision is deliberately different from normal runtime-owned actuator hardware.

The platform video service owns normal camera capture.

```text
Physical Camera
      ↓
Video / Vision Service
      ↓
Shared frame consumers
```

This avoids having the runtime and video service compete for the camera.

The robot runtime controls the physical camera mount servos, while the vision
service manages image capture and distribution.

These are separate resources:

```text
Camera Mount
    └── pan / tilt servos
            ↓
        Robot Runtime

Camera Sensor
    └── frames
            ↓
       Vision Service
```

Keeping those responsibilities separate allows the camera image stream to be
shared while physical camera movement remains protected by runtime control
ownership.

## Audio and the Runtime

Audio is not treated as normal runtime actuator hardware.

The audio subsystem and platform audio services manage speech and playback
through the configured audio backend.

This avoids forcing unrelated audio playback through the robot actuator
control lease.

Runtime ownership should only be expanded to additional resources when shared
ownership actually requires centralized coordination.

## Runtime and Platform Services

Platform services consume runtime information for functions such as:

- status
- monitoring
- diagnostics
- hardware checks
- calibration

Services should not recreate robot hardware merely because they need status
information.

For example:

```text
Monitor
   ↓
Runtime / passive platform checks
   ↓
Current observable state
   ↓
Compare with previous state
   ↓
Event
```

This allows monitoring to continue while another application controls the
robot.

## Runtime and Launchpad

Launchpad is a client of the runtime architecture rather than an independent
robot implementation.

Different Launchpad features use the runtime differently:

```text
Manual Drive
    → long-lived actuator control session

Calibration
    → short-lived exclusive control operations

Status
    → read-only runtime state

Diagnostics
    → read-only runtime and health information
```

This distinction prevents pages that only display information from
unnecessarily blocking robot control.

## Runtime and CLI

CLI commands that inspect the robot should use runtime or platform-service
interfaces rather than constructing a second robot.

Administrative operations should respect the same ownership boundaries as
Launchpad and student applications.

The CLI is another platform interface, not a privileged alternate hardware
architecture.

## Busy Errors

When an application requests control while another application owns it, the
request fails rather than stealing control.

Higher layers may translate the runtime failure into `RobotBusyError`.

This gives callers a meaningful application-level condition:

```text
Robot is currently being used by another application.
```

Launchpad can translate this into an HTTP conflict response and show an
appropriate message to the user.

A busy robot is not the same as failed hardware.

Status and diagnostics should preserve that distinction.

## Runtime Errors

Runtime failures are represented separately from normal control conflicts.

Examples include:

- runtime unavailable
- runtime communication failure
- malformed runtime response
- hardware initialization failure
- invalid operation
- unexpected runtime failure

Callers should not treat every runtime error as evidence that the physical
robot is broken.

The platform health and diagnostic layers are responsible for adding the
appropriate context.

## Safe Application Behavior

Applications using the runtime should follow several rules.

### Acquire control only when necessary

Read-only operations should not acquire an actuator lease.

### Hold control only as long as necessary

Calibration previews should use short-lived leases.

Interactive drive sessions may hold control longer because continuous control
is the purpose of the session.

### Always release control

Use the provided context manager or equivalent cleanup behavior.

### Stop before releasing drive control

Drive clients should leave the motors in a safe stopped state.

### Do not bypass runtime ownership

Applications must not solve a busy runtime by independently constructing the
same physical hardware.

A control conflict is an application coordination condition, not permission
to bypass the runtime.

## Runtime Service

The runtime operates as a platform service so robot hardware can be
initialized independently of individual user applications.

This allows the platform to establish robot hardware once during startup and
keep it available as applications come and go.

The runtime service participates in normal Betabox:

- service management
- status
- diagnostics
- monitoring
- boot readiness

If the runtime cannot initialize the robot, the platform can report that
condition without requiring a student application to discover it first.

## Startup

At platform startup:

```text
systemd
   ↓
Robot runtime service
   ↓
Runtime initialization
   ↓
Hardware initialization
   ↓
Runtime ready
   ↓
Status / monitoring / applications
```

Platform readiness depends on the runtime reaching an appropriate usable
state.

Boot verification and diagnostics can distinguish runtime problems from other
service or system failures.

## Shutdown

Runtime shutdown should leave owned hardware in a safe state.

Conceptually:

```text
Stop accepting new control
        ↓
Release active control
        ↓
Stop actuators
        ↓
Close robot hardware
        ↓
Close runtime transport
        ↓
Process exits
```

Individual applications should not perform global hardware cleanup when they
disconnect from the runtime.

The runtime owns the hardware lifetime and is therefore responsible for final
hardware cleanup.

## Ownership Boundary

The key runtime rule is:

> Applications own control sessions. The runtime owns robot hardware.

This distinction prevents an application's lifetime from becoming the
hardware's lifetime.

A browser can disconnect.

A notebook can stop.

A calibration operation can finish.

A diagnostic can run.

None of those events should require destroying and reconstructing the
platform's entire robot hardware stack.

## Extending the Runtime

New runtime operations should be added only when they represent functionality
that benefits from centralized robot ownership.

Before adding an operation, determine:

1. Does it require access to runtime-owned robot state or hardware?
2. Is it read-only or actuator-controlling?
3. Does it require an exclusive control token?
4. What safe state is required if the operation fails?
5. Can an existing higher-level Robot API expose it instead?
6. Does it belong to another shared service, such as Vision, instead?

Not every subsystem automatically belongs inside the runtime.

The runtime should remain the coordination boundary for shared robot hardware,
not become a general-purpose RPC service for the entire platform.

## Testing

Runtime testing should cover both protocol correctness and ownership behavior.

Important areas include:

- client request and response handling
- runtime state
- control acquisition
- control release
- control-token validation
- competing control requests
- read-only access during active control
- invalid requests
- runtime errors
- safe cleanup

Automated runtime tests verify software coordination.

Changes affecting physical hardware should additionally be validated on a real
Betabox.

For example, tests can prove that a steering command was accepted by the
runtime, but real-hardware validation is required to prove that the steering
servo physically moved as expected.

## Architectural Rules

The following rules should remain true as the runtime evolves:

1. The runtime is the long-lived owner of normal robot hardware.
2. Applications do not independently construct competing robot hardware.
3. Actuator commands require an active control lease.
4. Only one actuator-control owner exists at a time.
5. Supported read-only operations remain available without actuator control.
6. Control conflicts are reported rather than resolved by stealing ownership.
7. Control release leaves actuators in a safe state.
8. Application disconnection does not determine hardware lifetime.
9. Camera capture remains owned by the shared vision service.
10. Higher-level Robot APIs remain the preferred interface for student code.
11. Platform status distinguishes runtime availability from physical hardware
    health.
12. New runtime responsibilities are added deliberately rather than turning
    the runtime into a general platform RPC layer.

## Related Documentation

- [Platform Architecture](architecture.md)
- [Calibration](calibration.md)
- [Betabox Launchpad](launchpad.md)
- [Platform Health and Diagnostics](platform-health.md)
- [Hardware](hardware.md)
- [Development](development.md)
