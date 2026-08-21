# Platform Health and Diagnostics

Betabox Robotics provides a shared platform-health system for observing,
classifying, diagnosing, and recording the state of a running Betabox.

The health system is used across the platform by:

- boot verification
- boot announcements
- platform monitoring
- event recording
- CLI status
- CLI doctor
- Launchpad Status
- Launchpad Diagnostics
- the Launchpad status HUD

These interfaces should consume common platform state and health definitions
rather than independently deciding whether the robot is healthy.

## Purpose

Platform health answers several related but distinct questions.

```text
Observation
    │
    └── What can the platform currently observe?

Health
    │
    └── Is the observed state acceptable?

Status
    │
    └── What is happening right now?

Diagnostics
    │
    └── What appears to be wrong, and what should be checked?

Monitoring
    │
    └── How has the state changed over time?

Events
    │
    └── Which meaningful changes should be recorded?
```

Keeping these responsibilities separate prevents individual interfaces from
developing contradictory definitions of platform health.

## Health Architecture

Conceptually:

```text
Robot Runtime ────────────────┐
Passive Hardware Checks ──────┤
Vision Service ───────────────┤
systemd Services ─────────────┤
Host System Health ───────────┤
Networking ───────────────────┤
JupyterHub ───────────────────┘
               │
               ▼
        Platform Status
               │
               ▼
        Health Evaluation
          ┌────┼────┐
          │    │    │
          ▼    ▼    ▼
       Status Doctor Monitor
                       │
                       ▼
                     Events
```

Launchpad and CLI interfaces then present this shared information in forms
appropriate to their users.

## Sources of Health Information

The platform combines information from several sources.

### Robot Runtime

The centralized runtime provides information about the running robot,
including state such as:

- runtime readiness
- hardware ownership
- hardware initialization
- current control owner
- observable robot sensor data

Runtime state is important, but runtime readiness alone does not prove that
every physical component works.

### Passive Hardware Checks

Hardware that can be observed safely is checked without physically actuating
the robot.

Current passive checks include areas such as:

- Robot HAT / I2C communication
- battery
- grayscale sensor
- ultrasonic sensor

These checks can run while the robot is otherwise in use.

### Vision

Vision health is obtained through the shared vision service rather than by
opening another camera instance.

Relevant state includes:

- vision service availability
- camera running state
- usable frame availability
- vision errors where available

### Services

The platform observes managed systemd services required for normal operation.

Service state is included in platform status and monitoring.

### Host System

Host health includes operating-system and Raspberry Pi conditions such as:

- CPU temperature
- memory usage
- disk usage
- current undervoltage
- historical undervoltage
- current throttling
- historical throttling

### Networking

Platform status can include network state such as:

- Ethernet connectivity
- Wi-Fi connectivity

Network state should not automatically determine whether local classroom robot
operation is healthy.

Normal Betabox use is designed to work without an Internet connection.

### JupyterHub

JupyterHub health distinguishes between service state and application
responsiveness.

For example, a systemd service may be active while its HTTP endpoint is not
responding.

Those are different observations and should remain distinguishable.

## Passive Hardware Health

A central principle of Betabox health monitoring is:

> Only claim that the platform can verify what it can actually observe.

Some physical hardware exposes meaningful feedback.

Other hardware can only be commanded.

This distinction determines what can be monitored continuously.

## Observable Hardware

### Robot HAT / I2C

The platform can determine whether expected Robot HAT communication is
available.

Loss of the expected hardware communication can indicate conditions such as:

- Robot HAT powered off
- Robot HAT unavailable
- I2C communication failure
- hardware connection problem

Because several robot components depend on the Robot HAT, this is an important
platform-level condition.

### Battery

Battery voltage can be read and classified.

Battery state can therefore be monitored while the robot is running.

Typical state transitions include:

```text
unknown → ok
ok → low
low → critical
critical → ok
ok → unknown
```

The exact voltage thresholds are defined by the configured robot/platform
behavior rather than by Launchpad presentation code.

### Grayscale Sensor

The platform can read the three grayscale channels.

Health monitoring distinguishes between:

- sensor availability
- reading plausibility

This is important because a sensor can technically return values while still
producing readings that strongly suggest a disconnected or faulty module.

The platform can therefore represent conditions such as:

```text
Grayscale sensor available
Grayscale sensor unavailable
Grayscale readings available
Grayscale readings abnormal
```

Where possible, suspicious individual channels can also be identified.

### Ultrasonic Sensor

The ultrasonic sensor can be actively read without taking actuator control.

The platform can therefore monitor whether a usable ultrasonic reading can be
obtained.

Availability transitions can be recorded while the robot is running:

```text
Ultrasonic sensor became unavailable
Ultrasonic sensor became available
```

An ultrasonic failure does not require taking drive control from the current
application.

### Camera

Camera health is observed through the shared vision service.

The platform distinguishes between:

- service availability
- camera running
- usable frame available

This allows it to identify cases where the vision service exists but the
camera is not actually producing usable frames.

## Hardware That Cannot Be Passively Verified

Not every physical device provides feedback proving that it operated.

### Drive Motors

The platform can issue a motor command.

Without independent feedback such as encoders, it cannot prove that the
physical motor actually turned.

### Steering Servo

The platform can command the steering servo.

Without positional feedback, it cannot prove that the steering mechanism
physically reached the requested position.

### Camera Servos

The platform can command camera pan and tilt.

Without positional feedback, it cannot prove that the mount physically moved.

### Audio Output

The platform can verify portions of the audio software and hardware path and
can attempt playback.

It cannot passively prove that audible sound actually came from the speaker.

## Passive Health vs. Active Validation

The platform therefore distinguishes:

```text
Passive Health Monitoring
        │
        └── safe observation while the robot runs

Active Hardware Validation
        │
        └── deliberately operate hardware and observe the result
```

Passive health is appropriate for:

- boot checks
- continuous monitoring
- Status
- events
- non-invasive diagnostics

Active validation is required to prove physical behavior of devices such as:

- motors
- steering
- camera servos
- audible speaker output

The platform must not report those devices as physically verified merely
because a command API exists.

## Platform Status

Platform status is a snapshot of current observable state.

It combines information from the runtime, hardware, services, host system,
networking, vision, and other platform components.

Status is primarily descriptive.

It answers:

> What is the state of the platform right now?

Status should preserve useful detail rather than collapsing every condition
into one boolean.

For example:

```text
Runtime ready:               Yes
Hardware owned:              Yes
Hardware initialized:        Yes
Control owner:               None
Battery:                     OK
Grayscale:                   Available
Ultrasonic:                  Available
Vision service:              Available
Camera frame:                Available
```

This is more useful than simply reporting:

```text
Robot: OK
```

## Platform Health

Health evaluation interprets platform status.

Conceptually:

```text
StatusReport
     │
     ▼
evaluate_platform_health(...)
     │
     ▼
PlatformHealthData
```

The health evaluator is the shared place for determining the platform's
overall health from observable status.

Interfaces should consume this result rather than creating unrelated
definitions of overall platform health.

## Overall Health

The platform uses health classifications appropriate to the severity of the
observed conditions.

The user-facing model is generally:

```text
Healthy
Warning
Critical
```

### Healthy

The platform has no known condition requiring attention.

Healthy does not mean that every physical component has been mechanically
verified.

It means that all currently observable required platform conditions are in an
acceptable state.

### Warning

A warning indicates a condition requiring attention that does not necessarily
make the entire platform unusable.

Examples may include:

- low battery
- one observable sensor unavailable
- abnormal grayscale readings
- camera service available but no usable frame
- high resource usage
- previous undervoltage
- previous throttling
- JupyterHub service active but HTTP endpoint unavailable

### Critical

A critical condition indicates a serious platform problem or loss of an
important required capability.

Examples may include:

- required robot hardware unavailable
- critical battery state
- required service failure
- vision service unavailable where treated as required
- current severe host-system condition
- current undervoltage where it threatens reliable operation

Severity should be determined by shared platform policy rather than by CSS or
page-specific JavaScript.

## Unknown State

Unknown information should not silently become healthy.

An unknown reading may mean:

- the value has not been collected yet
- a dependent service is unavailable
- hardware could not be queried
- the state is not applicable
- the platform is still starting

Whether an unknown value affects overall health depends on what the value
represents.

Interfaces should preserve the distinction between:

```text
healthy
unhealthy
unknown
```

where that distinction matters.

## Runtime Health

Runtime state is part of overall platform health.

Important runtime conditions include:

- runtime available
- runtime ready
- hardware ownership acquired
- hardware initialized
- current control owner

A robot being actively controlled is not unhealthy.

For example:

```text
Control owner: Launchpad Manual Drive
```

is normal runtime state.

Likewise, an application receiving a robot-busy error because another
application owns control is not evidence of failed hardware.

## Service Health

Managed services are observed independently.

Relevant states can include:

```text
active
inactive
activating
failed
unknown
```

Not every inactive service is necessarily unhealthy.

Service-health policy must take the expected lifecycle of each service into
account.

For example, a one-shot boot service may legitimately become inactive after
successful completion.

The platform should not classify every non-active service as a failure without
considering that service's intended behavior.

## Vision Health

Vision health distinguishes several layers.

```text
Vision service reachable?
        ↓
Camera running?
        ↓
Usable frame available?
```

This allows diagnostics to distinguish:

```text
Vision service unavailable
```

from:

```text
Vision service available, but camera not producing frames
```

Those conditions have different likely causes and should not be reduced to the
same message.

## Grayscale Plausibility

Grayscale monitoring goes beyond checking whether an ADC read succeeded.

A physically disconnected or faulty grayscale module may still result in
numeric readings.

The platform therefore evaluates whether readings appear plausible.

Possible state includes:

- available and plausible
- available but suspicious
- unavailable

When suspicious channels can be identified, diagnostics and Launchpad may
provide more specific guidance.

For example:

```text
Left grayscale sensor may be disconnected or faulty.
```

or:

```text
The grayscale module may be disconnected or faulty.
```

when all channels appear suspicious.

This is a health heuristic, not absolute proof of physical failure.

## Calibration vs. Sensor Health

Sensor calibration and sensor availability are separate concepts.

For grayscale:

```text
Sensor health
    → Can the sensor be read?
    → Are its raw readings plausible?

Calibration
    → What raw values represent floor and line?
```

An uncalibrated grayscale module can still be physically healthy.

Likewise, saved calibration does not prove that the sensor is currently
connected.

Health and calibration must therefore remain separate.

## Status Interface

The CLI status command and Launchpad Status page present current platform
state.

They should consume shared status/health information.

Presentation can differ:

```text
CLI
    → concise textual summary

Launchpad
    → visual overview, details, and attention items
```

The underlying interpretation should remain consistent.

## Attention Items

Launchpad can translate health conditions into attention items.

An attention item contains user-facing information such as:

- title
- message
- severity

Examples include:

```text
Battery Low
Ultrasonic Unavailable
Grayscale Sensor Warning
Vision Not Ready
CPU Temperature High
Undervoltage Detected
```

Attention items are presentation of platform conditions.

They should not become an independent health engine.

## Diagnostics

Diagnostics provide a deeper interpretation of platform state.

Diagnostics answer:

> What appears to be wrong, and what should I check?

A diagnosis can include:

- check name
- result
- severity
- explanation
- likely cause
- troubleshooting guidance

Diagnostics should reuse the same observations that feed status and health.

They may perform additional safe checks where appropriate, but they should not
contradict the shared platform state.

## Doctor

`betabox doctor` is the command-line diagnostic interface.

Run:

```bash
betabox doctor
```

Doctor provides more detailed troubleshooting than:

```bash
betabox status
```

The two commands serve different purposes:

```text
betabox status
    → current platform state

betabox doctor
    → diagnostic interpretation and troubleshooting
```

Launchpad follows the same Status/Diagnostics distinction.

## Verification Checks

Verification checks determine whether expected platform capabilities are
available.

They are used for startup and other platform verification workflows.

Checks can cover areas such as:

- required hardware communication
- camera
- audio infrastructure
- robot construction/runtime readiness
- observable sensors

Verification checks should remain safe for their execution context.

A boot verification process should not unexpectedly drive motors simply to
prove that they work.

## Boot Health

Startup health is an important special case.

At boot, the platform needs to determine whether it has reached a usable
state.

Conceptually:

```text
Boot
  ↓
Services start
  ↓
Runtime initializes
  ↓
Verification checks
  ↓
Ready / troubleshooting needed
```

Boot verification should account for observable required hardware rather than
only checking that processes exist.

For example, a running service does not by itself prove:

- Robot HAT communication
- ultrasonic availability
- grayscale availability
- camera frame availability

## Boot Announcements

The boot announcer provides audible startup feedback.

Its purpose is to communicate whether the platform appears ready without
requiring the user to first open a terminal or browser.

Conceptually:

```text
Betabox starting
       ↓
Verification
       ↓
 ┌─────┴─────┐
 │           │
Ready      Failures
 │           │
 ▼           ▼
Ready     Announce relevant
for use   troubleshooting
```

The boot announcer consumes verification results rather than maintaining an
unrelated hardware-health implementation.

A failure announcement should correspond to an actual platform check.

## Continuous Monitoring

The Betabox monitor periodically collects platform state while the robot is
running.

Monitoring is intentionally passive.

It should not take actuator control merely to determine health.

The monitor:

1. collects current observable state;
2. compares it with the previous state;
3. identifies meaningful transitions;
4. logs those transitions;
5. records appropriate events.

Conceptually:

```text
Current State
     │
     ▼
Previous State
     │
     ▼
Compare
     │
     ├── no meaningful change → nothing
     │
     └── meaningful change
                ↓
              Event
```

## Monitoring Interval

Health monitoring runs periodically rather than continuously polling hardware
as fast as possible.

The configured monitoring interval determines how quickly passive state
changes are normally detected.

This means an event timestamp represents when the monitor observed a
transition, not necessarily the exact physical instant when the condition
began.

## Initial Monitor State

When the monitor starts, it records an initial snapshot.

That snapshot establishes the baseline for future comparisons.

Initial state should not automatically generate a historical transition for
every field because there is no previous observation to compare against.

After the baseline exists, changes can generate events.

## Events

Events record meaningful changes in platform state.

They provide historical information that a current status snapshot cannot.

For example:

```text
11:41:02 [WARNING] hardware: Ultrasonic sensor became unavailable
11:44:03 [INFO]    hardware: Ultrasonic sensor became available
```

Current status may show:

```text
Ultrasonic: Available
```

while the event history reveals the earlier interruption.

## Event Categories

Events can be grouped by the part of the platform that changed.

Examples include:

```text
hardware
services
system
runtime
vision
```

Categories make it easier to understand where a condition originated.

## Event Severity

Events use severity appropriate to the transition.

Common levels include:

```text
INFO
WARNING
ERROR
CRITICAL
```

Examples:

```text
INFO
    → a previously unavailable sensor recovered

WARNING
    → an individual sensor became unavailable

ERROR
    → robot hardware became unavailable

CRITICAL
    → a severe platform condition requiring immediate attention
```

Severity should reflect the significance of the event rather than simply the
fact that something changed.

## Recovery Events

Recovery is important enough to record.

For example:

```text
Grayscale sensor became unavailable
```

should later be paired with:

```text
Grayscale sensor became available
```

when the condition clears.

Without recovery events, the event history would show failures without
revealing whether they remain current.

## State Changes vs. Repeated Errors

The monitor should generally record transitions rather than repeatedly logging
the same unchanged failure every monitoring cycle.

Preferred:

```text
11:00 Ultrasonic sensor became unavailable
11:05 Ultrasonic sensor became available
```

Not:

```text
11:00 Ultrasonic unavailable
11:01 Ultrasonic unavailable
11:02 Ultrasonic unavailable
11:03 Ultrasonic unavailable
11:04 Ultrasonic unavailable
```

Transition-based events reduce noise and make the event history useful.

## Current State vs. Event History

Status and Events answer different questions.

```text
Status
    → What is true now?

Events
    → What changed?
```

A resolved historical event should not make current Status unhealthy.

Likewise, a current failure should not disappear merely because its event has
already been recorded.

## System Health

Host system health includes conditions that can affect robot reliability.

### CPU Temperature

Temperature can be classified into states such as:

```text
normal
warning
critical
```

High temperature can reduce performance or eventually threaten stable
operation.

### Memory

Memory usage is monitored for significant resource pressure.

High memory usage may indicate a runaway application or insufficient available
resources.

### Disk

Disk usage is monitored because a nearly full filesystem can interfere with:

- logging
- media
- notebooks
- application state
- updates

### Undervoltage

Raspberry Pi undervoltage is an important platform-health signal.

The platform distinguishes:

- undervoltage occurring now
- undervoltage occurred since boot

A current condition is more severe than a historical condition that has
cleared.

### Throttling

The platform similarly distinguishes:

- currently throttled
- throttling occurred since boot

Historical throttling remains useful diagnostic information even after the
current condition clears.

## Network Health

Network information is useful for troubleshooting access to Launchpad and
JupyterHub.

However:

```text
No Internet
```

is not equivalent to:

```text
Betabox unhealthy
```

The platform is intentionally designed for offline classroom operation.

Health evaluation should focus on networking required for the robot's intended
current operating mode.

## Health and Control Ownership

Control ownership is operational state, not health failure.

For example:

```text
Control owner: Student Program
```

means the runtime is being used normally.

If Calibration then receives a busy error, the appropriate interpretation is:

```text
Robot currently in use
```

not:

```text
Robot hardware failed
```

Status, diagnostics, and Launchpad should preserve this distinction.

## Health and Startup Timing

Platform services do not all become ready simultaneously.

During startup, transient states such as:

```text
activating
starting
unknown
```

may be expected.

Health evaluation should avoid reporting expected startup progression as a
permanent failure.

Boot verification should wait appropriately for required services and hardware
before making a final readiness determination.

## Failure Isolation

A failure in one platform component should not automatically make unrelated
components appear unavailable.

Examples:

- JupyterHub can fail while Manual Drive remains usable.
- Vision can fail while sensor status remains available.
- Ultrasonic can fail while drive control remains usable.
- Manual Drive can be busy while diagnostics remain readable.
- Internet access can be absent while the local classroom platform works.

Health data should therefore preserve component-level state.

## Error Messages

Health and diagnostic messages should be specific enough to guide
troubleshooting.

Prefer:

```text
Ultrasonic sensor unavailable.
```

over:

```text
Robot error.
```

Prefer:

```text
Vision service is available, but the camera is not producing a usable frame.
```

over:

```text
Camera failed.
```

More specific observations allow users to check the correct part of the
platform.

## Avoiding False Certainty

Health checks should avoid claims stronger than their evidence.

For example:

If an I2C device responds, it is reasonable to report:

```text
Robot HAT communication available
```

It is not sufficient evidence to report:

```text
All robot hardware working
```

Likewise, successfully sending a motor command proves software command
delivery, not physical motor motion.

Health terminology should reflect what was actually measured.

## Adding a Health Check

Before adding a new health check, determine:

1. What exact condition is being observed?
2. Can it be checked safely while the robot is in use?
3. Does it require actuator control?
4. Is the result direct evidence or a heuristic?
5. What does unavailable mean?
6. What does recovery look like?
7. What severity should failure have?
8. Should the condition affect overall platform health?
9. Should a transition generate an event?
10. Should boot verification consider it?
11. What troubleshooting information can Diagnostics provide?

A check should not be added independently to only one interface when the same
condition matters platform-wide.

## Adding a Monitored State

For a new continuously monitored condition:

```text
Collect
   ↓
Normalize
   ↓
Include in monitor snapshot
   ↓
Compare with previous snapshot
   ↓
Generate transition events
```

Both failure and recovery behavior should be defined.

The initial state should also be considered so monitor restarts do not create
misleading transitions.

## Adding a Diagnostic

A diagnostic should build on an established observation wherever possible.

For example:

```text
Observation:
    ultrasonic_available = false

Diagnostic:
    Ultrasonic sensor could not be read.
    Check the sensor connection and cable.
```

The diagnostic adds explanation.

It should not create a second unrelated definition of whether the ultrasonic
sensor is available.

## Adding Launchpad Presentation

Launchpad presentation should consume the shared state.

For example:

```text
Platform health
      ↓
Status API
      ↓
Launchpad JavaScript
      ↓
Attention item
```

JavaScript may choose appropriate labels and presentation, but server-side
platform state remains authoritative.

## Testing Health Behavior

Health testing should cover both individual observations and their
interpretation.

Important areas include:

- runtime state
- service states
- Robot HAT availability
- battery classification
- grayscale availability
- grayscale plausibility
- ultrasonic availability
- vision availability
- camera frame availability
- system-health thresholds
- overall health evaluation
- diagnostics
- monitor transitions
- failure events
- recovery events
- initial monitor state
- boot verification

Tests should include transitions such as:

```text
available → unavailable
unavailable → available

ok → low
low → critical
critical → ok

normal → warning
warning → normal
```

This is especially important for monitoring because detecting the current
state and detecting a state transition are separate behaviors.

## Real-Hardware Validation

Automated tests cannot replace physical validation of health heuristics.

Real Betabox testing should include intentionally creating safe failure
conditions where practical.

Examples include:

- disconnecting the ultrasonic sensor
- disconnecting the grayscale module
- disabling Robot HAT power
- stopping the vision service
- preventing usable camera frames
- stopping a managed service

For each test, verify the complete path where applicable:

```text
Physical condition
      ↓
Observation
      ↓
Status
      ↓
Health classification
      ↓
Diagnostics
      ↓
Monitor
      ↓
Event
      ↓
Recovery
```

This ensures the platform is not merely detecting a condition in one isolated
interface.

## Architectural Rules

The following rules should remain true as platform health evolves:

1. Platform health is shared infrastructure.
2. Status describes current observable state.
3. Health evaluates that state.
4. Diagnostics explain unhealthy or suspicious conditions.
5. Monitoring observes state over time.
6. Events record meaningful transitions.
7. Boot verification uses established platform checks.
8. Launchpad does not maintain an independent hardware-health implementation.
9. CLI interfaces and Launchpad should agree about underlying platform state.
10. Passive monitoring must not unexpectedly actuate the robot.
11. Control ownership is not a hardware failure.
12. Unknown state must not silently become healthy.
13. Hardware checks must not claim more than they can observe.
14. Actuators without feedback cannot be passively proven physically healthy.
15. Sensor availability and sensor calibration are separate concepts.
16. Failure and recovery transitions should both be represented.
17. Repeated unchanged failures should not flood the event history.
18. A resolved historical event should not make current Status unhealthy.
19. Component failures should remain isolated where possible.
20. New health conditions should be integrated across the appropriate shared
    layers rather than patched into one interface.

## Related Documentation

- [Platform Architecture](architecture.md)
- [Central Robot Runtime](runtime.md)
- [Betabox Launchpad](launchpad.md)
- [Calibration](calibration.md)
- [Installation](installation.md)
- [Hardware](hardware.md)
- [Development](development.md)
