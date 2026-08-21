# Betabox Launchpad

Betabox Launchpad is the browser-based user interface for the Betabox Robotics
platform.

It provides students and operators with access to robot control, programming,
vision, media, calibration, status, diagnostics, services, events, and
platform information without requiring direct command-line access.

Launchpad runs locally on the Betabox and is designed for normal classroom use
without requiring an Internet connection.

## Purpose

Launchpad provides a single browser interface to the major capabilities of the
Betabox platform.

Its responsibilities include:

- presenting robot controls
- providing access to JupyterHub
- displaying the shared vision stream
- managing classroom media
- performing robot calibration
- displaying platform status
- running diagnostics
- displaying service state
- displaying platform events
- presenting robot and system information
- managing user preferences

Launchpad is an interface to the existing Betabox platform.

It does not implement a separate robot hardware stack.

```text
Browser
   │
   ▼
Launchpad
   │
   ├── Robot Runtime
   ├── Vision Service
   ├── Platform Services
   ├── Calibration Services
   ├── JupyterHub
   └── User Workspace
```

## Architectural Boundary

Launchpad should contain browser and application-interface behavior.

Reusable robot functionality belongs below Launchpad.

For example:

```text
Browser button
      ↓
Launchpad route / WebSocket
      ↓
Application service or runtime client
      ↓
Robot Runtime
      ↓
Robot hardware
```

Launchpad should not construct competing motors, servos, sensors, or complete
robot instances simply because a browser page needs access to them.

This keeps browser behavior consistent with student code, CLI tools, platform
services, and other applications.

## Local Operation

Launchpad is hosted by the Betabox itself.

Normal classroom operation is designed to work over the robot's local network
without an external Internet connection.

This allows a classroom workflow such as:

```text
Student device
      │
      ▼
Betabox local network
      │
      ├── Launchpad
      ├── JupyterHub
      ├── Vision
      └── Robot services
```

External network access may be useful for development or administration, but
it is not a requirement for normal robot use.

## Launchpad Pages

Current Launchpad functionality includes:

- Home
- Manual Drive
- Code
- Vision
- Media
- Calibration
- Status
- Diagnostics
- Services
- Events
- Information

These pages share the same platform identity, workspace, permissions, and
status infrastructure.

## Home

The Home page is the primary Launchpad entry point.

It provides access to the major classroom tools and presents a compact view of
robot state through the Launchpad HUD.

The Home page should remain an overview rather than duplicating the complete
Status or Diagnostics interfaces.

## Status HUD

Launchpad provides a compact status HUD for information that is useful while
working elsewhere in the application.

The HUD summarizes important platform state without requiring the user to
leave the current page.

The HUD consumes shared platform status information rather than independently
probing hardware.

Its classification should remain consistent with the detailed Status page and
platform health system.

## Manual Drive

Manual Drive provides interactive browser control of the robot.

It participates in centralized runtime control ownership.

Conceptually:

```text
Browser
   ↓
Manual Drive
   ↓
Launchpad control session
   ↓
RobotRuntimeClient
   ↓
Runtime control lease
   ↓
Drive / steering
```

Manual Drive does not directly own GPIO or construct independent drive
hardware.

### Control Ownership

Manual Drive must acquire robot control before issuing actuator commands.

Only one application can own actuator control at a time.

If another application owns the robot, Manual Drive cannot silently take
control away from it.

Likewise, while Manual Drive owns control, another actuator-controlling
application such as Calibration cannot acquire control.

A control conflict is an expected application state and should be presented
to the user as such rather than reported as failed hardware.

### Control Lifetime

Manual Drive differs from short calibration operations because it represents
an interactive control session.

The control lease may therefore remain active while the browser is actively
using Manual Drive.

When the session ends or control is lost, the platform must leave the drive
hardware in a safe state and release control.

### Live Status

Manual Drive can continue displaying supported read-only robot information
while it owns actuator control.

This may include information such as:

- battery state
- temperature
- runtime state
- sensor information
- connection state

Read-only information does not require a second control lease.

## Code

The Code page provides browser access to the Betabox programming environment.

JupyterHub is the primary notebook environment for student Python code.

Launchpad acts as the entry point rather than implementing a separate notebook
system.

Conceptually:

```text
Launchpad Code
      ↓
JupyterHub
      ↓
Betabox robot kernel
      ↓
Public Robot API
      ↓
Central Robot Runtime
```

Students should normally program the robot through the high-level Robot API:

```python
from betabox_robotics import Robot

robot = Robot.default()
```

Students are not expected to manage runtime transport or physical GPIO
ownership themselves.

## Vision

The Vision page provides browser access to the platform's shared camera
service.

Normal camera capture is owned by the vision/video service rather than by the
Launchpad process.

```text
Physical Camera
      ↓
Vision Service
      ↓
Launchpad Vision
```

This allows camera frames to be shared without Launchpad independently opening
the physical camera.

Vision functionality may include:

- live camera viewing
- stream state
- snapshots
- recording
- other supported vision operations

Camera image ownership and camera-mount ownership are intentionally separate.

The vision service owns image capture.

The centralized robot runtime owns physical pan and tilt servo control.

## Media

The Media page provides access to user media stored in the Launchpad
workspace.

Supported media operations include:

- viewing media
- uploading media
- downloading media
- working with supported pictures
- working with supported videos
- working with supported sounds

Media belongs to the active user workspace.

This is important because workspace persistence differs between guest and
student sessions.

## Calibration

The Calibration page is the normal user interface for configuring physical
robot calibration.

Current calibration areas include:

- steering center
- camera pan
- camera tilt
- left motor trim
- right motor trim
- grayscale floor references
- grayscale line references

Calibration is split between persisted values and physical preview
operations.

```text
Calibration page
       │
       ├── Calibration Service
       │       └── validation / persistence
       │
       └── Calibration Hardware
               └── Robot Runtime
                       └── physical preview
```

Launchpad should not duplicate calibration validation that must be enforced by
the application/service layer.

Client-side validation may improve the user experience, but invalid
calibration must still be rejected by the server-side calibration model or
service.

### Grayscale Calibration

Grayscale calibration records floor and line references for all three sensor
channels.

Every floor/line pair must have sufficient separation to create a usable
calibration.

The current minimum required separation is:

```text
100
```

A calibration that does not meet this requirement cannot be saved.

This protects robot behavior from invalid configurations such as identical or
nearly identical floor and line readings.

### Reset

The Calibration page provides a Reset action for returning the robot to its
uncalibrated defaults.

A full reset coordinates physical hardware and persisted calibration.

The operation:

1. acquires runtime control;
2. stops the motors;
3. returns steering to its uncalibrated physical center;
4. returns camera pan and tilt to their uncalibrated physical centers;
5. releases runtime control;
6. resets persisted calibration values.

If another application owns robot control, the reset is rejected rather than
clearing persisted calibration without first being able to safely reset the
physical actuators.

See [Calibration](calibration.md) for the authoritative calibration behavior.

## Status

The Status page provides a detailed view of current platform state.

It consumes shared platform status information rather than implementing its
own independent hardware probes.

Current status areas include information about:

- overall platform health
- runtime state
- hardware ownership
- hardware initialization
- current control owner
- battery
- grayscale sensor
- ultrasonic sensor
- vision
- JupyterHub
- services
- CPU temperature
- memory
- disk
- throttling
- undervoltage
- networking

The Status page is primarily observational.

It answers:

> What is the state of the platform right now?

It should not become a second diagnostics implementation.

## Overall Health

Launchpad presents an overall platform-health classification.

The overall state is derived from the same underlying platform conditions used
by status and diagnostic interfaces.

Typical classifications include:

```text
Healthy
Warning
Critical
```

Individual attention items explain conditions contributing to a non-healthy
state.

The UI should not classify the platform as healthy merely because the
Launchpad HTTP service itself is responding.

## Attention Items

The Status page highlights conditions requiring attention.

Examples include:

- failed services
- Robot HAT unavailable
- critical or low battery
- grayscale sensor unavailable
- abnormal grayscale readings
- ultrasonic sensor unavailable
- vision unavailable
- high CPU temperature
- memory pressure
- disk pressure
- current undervoltage
- previous undervoltage
- CPU throttling
- JupyterHub not responding

Attention items translate raw platform state into information meaningful to a
user troubleshooting the robot.

They should remain aligned with the central platform-health definitions.

## Diagnostics

The Diagnostics page provides deeper troubleshooting information than the
Status page.

Where Status asks:

> What is happening?

Diagnostics should help answer:

> What is wrong, and what should I check?

Diagnostics can provide:

- individual checks
- severity
- explanation
- likely causes
- troubleshooting guidance
- overall diagnostic result

Diagnostics should use shared diagnostic services rather than reimplementing
checks in JavaScript.

Browser code is responsible for presenting diagnostic results.

The diagnostic service is responsible for deciding what those results mean.

## Services

The Services page presents the state of managed Betabox platform services.

Managed services include platform components such as:

- robot runtime
- Launchpad
- vision
- monitoring
- JupyterHub
- boot announcements
- Wi-Fi fallback
- hostname configuration
- guest workspace management

The exact managed-service registry is defined by the current platform
configuration and services layer.

The Services page should use that registry rather than maintaining a separate
hard-coded definition of the platform.

## Events

The Events page presents meaningful state transitions recorded by the platform
monitor.

Events provide historical context that current Status cannot provide.

For example:

```text
11:01  Ultrasonic sensor became unavailable
11:04  Ultrasonic sensor became available
```

Current status may show the sensor as healthy, while Events reveals that a
temporary failure occurred earlier.

Events can include changes involving:

- services
- runtime
- robot hardware
- battery
- grayscale sensor
- ultrasonic sensor
- vision
- system health
- networking

Events include severity information so the interface can distinguish normal
state changes from warnings and critical failures.

See [Platform Health and Diagnostics](platform-health.md).

## Information

The Information page presents robot and platform information that does not
belong in the live troubleshooting interfaces.

It also provides Launchpad appearance and accessibility preferences.

Preferences belong to the active Launchpad workspace rather than being
treated solely as browser-local state.

This ensures that persistence follows the active user model.

## Identity and User Context

Every Launchpad request operates within a Launchpad context.

The context identifies the active user and supplies:

- identity
- permissions
- workspace
- platform context
- service access

Launchpad routes should consume this context rather than independently
determining user identity or workspace paths.

## Roles

The current student-facing Launchpad model defines:

- Guest
- Student

Teacher and administrator-specific Launchpad functionality is not currently
part of the implemented role model.

Guest and student users currently have the same normal functional access to
student-facing Launchpad capabilities.

The important difference is persistence.

## Permissions

Launchpad represents access using explicit permissions.

Current user-facing capabilities include permissions for areas such as:

- robot drive
- code
- vision
- media viewing
- media upload
- media download
- calibration
- status
- diagnostics
- services
- information
- preference changes
- events

Guest and student users currently receive the same normal user permission set.

The permission system establishes a boundary that can support additional role
differences later without scattering username checks throughout routes.

## Guest Workspaces

Guest sessions use a temporary workspace.

Guest workspace data is non-persistent.

This includes user data such as:

- code
- media
- preferences
- other workspace state

The guest experience should remain functionally useful while ensuring that
temporary classroom work does not become permanent account data.

## Student Workspaces

Student sessions use persistent workspaces.

Student data remains available between sessions.

Persistent workspace data includes areas such as:

- code
- media
- preferences

This allows students to return to their work while preserving the same
functional Launchpad interface used by guests.

## Workspace Model

A Launchpad workspace provides paths for user-managed resources.

Conceptually:

```text
Workspace
   │
   ├── curriculum
   ├── media
   │    ├── pictures
   │    ├── videos
   │    └── sounds
   └── preferences
```

The workspace determines persistence.

Application features should use workspace paths rather than hard-coded
per-user filesystem assumptions.

## Preferences

Launchpad preferences are workspace-managed.

This allows:

```text
Guest
   → temporary preferences

Student
   → persistent preferences
```

Appearance settings should therefore follow the Launchpad identity rather
than accidentally persisting forever in one browser's local storage.

Preferences may include supported interface options such as:

- appearance
- larger text
- reduced motion
- other accessibility or layout settings

## HTTP Routes

Launchpad HTTP routes are application boundaries.

Routes should generally:

1. validate the request;
2. obtain the Launchpad context;
3. check the required permission;
4. call the appropriate application service;
5. translate expected errors into HTTP responses;
6. serialize the result.

Routes should avoid implementing reusable robot behavior directly.

For example:

```text
POST calibration reset
       ↓
Permission check
       ↓
Calibration hardware reset
       ↓
Calibration service reset
       ↓
Serialized status
```

The route coordinates the operation.

The underlying services own the reusable behavior.

## WebSockets

Interactive features may use WebSockets where a persistent bidirectional
connection is appropriate.

Manual Drive is the primary example.

A WebSocket connection does not bypass runtime ownership.

Instead:

```text
Browser WebSocket
       ↓
Launchpad controller
       ↓
Runtime control lease
       ↓
Robot commands
```

Connection lifecycle and runtime-control lifecycle must be coordinated so that
an abandoned browser session does not leave the robot under stale control.

## JavaScript Responsibilities

Launchpad JavaScript should be responsible for browser behavior such as:

- API requests
- WebSocket communication
- DOM updates
- formatting
- interaction state
- client-side validation
- accessible UI feedback

JavaScript should not become the authoritative implementation of platform
health, calibration validity, permissions, or hardware behavior.

Those rules belong on the server or in shared platform services.

Client-side logic may mirror a server rule for immediate feedback, but the
server remains authoritative.

## Templates

Launchpad templates define the semantic page structure rendered by the server.

Templates should provide:

- meaningful document structure
- accessible labels
- stable element identifiers
- page sections appropriate to the feature

Dynamic state is then populated or updated by the relevant JavaScript module.

Presentation should remain separate from platform behavior.

## Styling

Launchpad uses shared styling and page-specific styles where appropriate.

UI components should be selected based on their purpose.

Examples include:

- cards for tools, actions, editing, and summaries
- property lists for detailed read-only information
- reading cards for live sensor values
- overview cards for dashboard summaries

Pages should not be forced into one visual component merely for consistency.

Consistency should come from the design system, typography, spacing, status
language, and interaction patterns.

## Status Presentation

Status should never rely on color alone.

A condition should be communicated using a combination of:

- text
- labels
- structure
- status indicators
- color where useful

For example:

```text
● Warning — Ultrasonic Unavailable
```

is preferable to presenting only a yellow dot.

This is important for accessibility and for clear classroom troubleshooting.

## Accessibility

Launchpad should remain usable with keyboard navigation and common assistive
technology.

Important accessibility areas include:

- visible keyboard focus
- semantic headings
- properly associated labels
- status text in addition to color
- reduced-motion support
- larger-text support
- useful ARIA/live-region behavior for dynamic state
- sufficient text contrast
- skip-to-content navigation where appropriate

Accessibility behavior should be implemented globally where possible rather
than independently on every page.

## Error Handling

Launchpad should distinguish different classes of failure.

Examples include:

```text
Bad request
    → invalid user input

Forbidden
    → permission denied

Conflict
    → robot currently busy

Service unavailable
    → required platform service unavailable

Internal error
    → unexpected application failure
```

A robot-busy condition should not be presented as broken hardware.

Likewise, invalid calibration should not be reported as an internal server
error.

Routes should translate known application errors into meaningful HTTP
responses.

## Launchpad and Platform Health

Launchpad consumes the platform health system but does not own it.

This is important because the same health definitions are needed by:

- boot verification
- monitoring
- CLI status
- CLI doctor
- Launchpad Status
- Launchpad Diagnostics
- events

The browser should not produce a contradictory definition of whether the
robot is healthy.

Where presentation-specific classification is necessary, it should derive
from the shared platform state.

## Launchpad and Services

Launchpad depends on several platform components but should degrade
intelligently when one is unavailable.

For example:

- Vision may be unavailable while Status still works.
- JupyterHub may be unavailable while Manual Drive still works.
- Robot actuator control may be busy while sensor status remains readable.
- A sensor may fail without making Launchpad itself unavailable.

This is why the platform models individual subsystem and service states rather
than reducing everything to a single online/offline flag.

## Security and Permissions

Launchpad permissions are enforced server-side.

Hiding a button in JavaScript is not authorization.

Any route performing a protected operation must verify the corresponding
permission using the active Launchpad context.

Client-side presentation may hide or disable unavailable actions for usability,
but it must not be the security boundary.

## Adding a Launchpad Feature

When adding a new feature, first determine where its behavior belongs.

```text
Is it reusable robot behavior?
    → robot/subsystem/runtime layer

Is it platform-level behavior?
    → services

Is it user identity or persistence?
    → Launchpad context/workspace

Is it HTTP translation?
    → route

Is it browser interaction?
    → JavaScript

Is it document structure?
    → template

Is it presentation?
    → CSS
```

A new browser feature often requires changes at several layers, but that does
not mean all of its logic belongs in Launchpad.

## Testing

Launchpad testing should cover important application boundaries such as:

- authentication/context
- permissions
- guest workspace behavior
- student workspace behavior
- route validation
- error translation
- Manual Drive control ownership
- calibration routes
- status serialization
- diagnostics
- services
- events
- preferences

Browser behavior should also be tested manually for interactions that are
difficult to represent through server-side unit tests.

Hardware-affecting Launchpad changes require real-robot validation.

For example, an automated route test can prove that a calibration reset calls
the expected services, but physical testing is required to verify that the
steering and camera mount actually return to the expected positions.

## Architectural Rules

The following rules should remain true as Launchpad evolves:

1. Launchpad is an interface to the Betabox platform, not a second hardware
   architecture.
2. Robot actuator control goes through centralized runtime ownership.
3. Shared camera capture goes through the vision service.
4. Reusable application behavior belongs below HTTP routes.
5. Server-side services remain authoritative for validation and platform
   rules.
6. Permissions are enforced on the server.
7. Guest and student functionality remains equivalent unless an intentional
   role distinction is introduced.
8. Guest data is temporary and student data is persistent.
9. Preferences follow the workspace persistence model.
10. Status, diagnostics, monitoring, events, and boot health should share
    common platform definitions.
11. Browser disconnection must not leave stale actuator control.
12. Launchpad must distinguish control conflicts from hardware failures.
13. Read-only interfaces should not acquire actuator control unnecessarily.
14. Accessibility is a platform-wide interface requirement rather than
    page-specific polish.
15. New features should be implemented at the lowest appropriate reusable
    layer.

## Related Documentation

- [Platform Architecture](architecture.md)
- [Central Robot Runtime](runtime.md)
- [Calibration](calibration.md)
- [Platform Health and Diagnostics](platform-health.md)
- [Installation](installation.md)
- [Hardware](hardware.md)
- [Development](development.md)
