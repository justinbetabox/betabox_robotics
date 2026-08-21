# Betabox Robotics

`betabox_robotics` is the software platform for the Betabox robotic car.

It provides a high-level Python API, centralized robot runtime, hardware and subsystem abstractions, browser-based Launchpad interface, system services, diagnostics, calibration, and deployment tooling for running Betabox robots in classroom environments.

The platform is designed to provide one consistent interface from low-level hardware access through student-facing applications.

## Goals

Betabox Robotics is designed around a few core principles:

- Provide a simple Python API for students and applications.
- Keep hardware-specific behavior behind reusable abstractions.
- Centralize ownership of robot hardware and control.
- Prevent applications from competing for motors, servos, sensors, or other hardware.
- Support browser-based robot control and diagnostics through Launchpad.
- Operate without requiring Internet access during classroom use.
- Provide useful health, status, diagnostic, and recovery information.
- Keep deployment and classroom maintenance predictable.

## Platform Architecture

The platform is layered so applications do not need to manage hardware directly.

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

The central robot runtime owns the robot hardware for the lifetime of the platform and exposes it to applications through runtime clients.

Applications that need exclusive actuator control acquire a control lease from the runtime. Read-only operations can use the runtime without taking control of the robot.

This allows Launchpad, student code, calibration, diagnostics, and platform services to share one running robot safely.

## Public Robot API

The primary Python interface is `Robot`.

```python
from betabox_robotics import Robot

robot = Robot.default()
```

For the current platform, `Robot.default()` creates the configured Betabox car interface.

The concrete car implementation can also be used directly:

```python
from betabox_robotics import BetaboxCar

robot = BetaboxCar()
```

The high-level API provides access to common classroom operations such as:

- driving forward and backward
- stopping
- steering left, right, and center
- ultrasonic distance
- grayscale / line sensor readings
- battery information
- camera snapshots
- recording
- vision streaming
- speech and audio
- robot identity and system information

Lower-level subsystem interfaces are available when more control is required.

## Central Robot Runtime

Robot hardware is coordinated by a centralized runtime.

The runtime is responsible for:

- hardware initialization
- hardware lifetime
- actuator ownership
- control leases
- drive commands
- steering
- camera mount control
- sensor access
- calibration previews
- runtime state
- safe shutdown

Applications communicate with the runtime rather than independently constructing competing hardware objects.

A single application may hold robot control at a time. Other applications can continue to perform supported read-only operations while control is held.

This architecture allows a student program, Manual Drive, calibration tools, diagnostics, and other platform components to coexist without relying on GPIO ownership as an application-level locking mechanism.

## Hardware Layer

The hardware package provides reusable abstractions for the physical devices used by the robot.

Current abstractions include:

- digital GPIO
- I2C
- ADC
- PWM
- motors
- servos

These abstractions are intentionally kept separate from robot-specific configuration.

Higher-level subsystems compose them into the configured Betabox robot.

## Drive

The drive subsystem manages:

- left and right motors
- steering servo
- steering limits
- motor direction
- motor trim
- calibration
- drive status

Applications should normally control movement through the Robot API or centralized runtime rather than constructing drive hardware directly.

## Sensors

The sensor subsystem currently includes:

- ultrasonic distance sensing
- three-channel grayscale sensing
- battery voltage monitoring

The platform can monitor readable sensors while the robot is running.

This allows failures and recoveries involving the battery, grayscale module, ultrasonic sensor, and other observable hardware to appear in platform status and event reporting.

## Vision

The vision subsystem provides shared camera functionality including:

- camera capture
- snapshots
- recording
- streaming
- frame distribution
- metadata
- detection infrastructure
- overlays

The platform video service owns normal camera operation so applications do not need to independently open the camera.

Launchpad and other clients can consume the shared vision service.

## Audio

The audio subsystem provides:

- speech
- sound playback
- notes
- melodies
- playback status
- audio device control

Audio output is configured for the Betabox platform hardware and can be accessed through the high-level Robot API.

## System

The system layer exposes platform information such as:

- robot identity
- version information
- network information
- media paths
- system status
- system health

Platform services build on these APIs to provide monitoring and diagnostics.

## Calibration

Betabox supports persistent calibration for:

- steering center
- camera pan and tilt
- left and right motor trim
- grayscale floor and line references

Calibration is normally performed through the Calibration page in Launchpad.

Grayscale calibration requires the floor and line readings for every sensor channel to differ by at least `100`. Invalid calibration cannot be saved.

Calibration can also be reset to the robot defaults. A full reset:

- stops the motors
- returns steering to its uncalibrated center
- returns the camera mount to its uncalibrated center
- restores default steering calibration
- restores default camera calibration
- restores default motor trim
- clears grayscale calibration

Calibration hardware operations use the centralized runtime and participate in normal robot control ownership.

## Betabox Launchpad

Launchpad is the browser-based interface for the Betabox platform.

It provides access to robot functionality without requiring command-line administration.

Current Launchpad functionality includes:

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

Launchpad is designed to work on the robot's local network and does not require Internet access for normal classroom use.

### Manual Drive

Manual Drive provides browser-based control of the robot while holding a runtime control lease.

It includes:

- movement controls
- steering
- live robot status
- battery information
- sensor information
- connection state

If another application owns robot control, Manual Drive cannot take control until the existing owner releases it.

### Status

Launchpad provides both a compact status HUD and a detailed Status page.

Observable platform state includes information about:

- robot runtime
- hardware availability
- battery
- grayscale sensor
- ultrasonic sensor
- vision
- services
- CPU temperature
- memory
- disk usage
- throttling
- undervoltage
- networking
- JupyterHub

### Diagnostics

Diagnostics provide more detailed checks and explanations when the platform is not healthy.

The diagnostic system is intended to distinguish between problems such as:

- service failures
- runtime failures
- Robot HAT / I2C problems
- sensor failures
- camera problems
- power problems
- system resource problems

Not every physical component can be passively verified.

Motors, steering servos, camera servos, and actual speaker output require active operation to prove that the physical device is working.

### Events

The platform monitor records meaningful state changes as events.

Examples include:

- hardware becoming available or unavailable
- battery state changes
- grayscale sensor failures and recoveries
- abnormal grayscale readings
- ultrasonic sensor failures and recoveries
- vision state changes
- service state changes
- system health changes

This provides a history of problems that may have occurred while the robot was running.

## User Workspaces

Launchpad supports guest and student workspace contexts.

Guest and student users currently have the same functional access to the normal student-facing Launchpad tools.

The primary difference is persistence:

- student workspace data persists
- guest workspace data is temporary

Workspace-managed data includes code, media, and Launchpad preferences.

## Platform Services

Betabox uses system services to keep the classroom platform running automatically.

Managed services include components for:

- centralized robot runtime
- Launchpad
- video / vision
- platform monitoring
- boot announcements
- JupyterHub
- Wi-Fi fallback
- hostname configuration
- guest workspace reset

The monitoring system continuously collects observable platform state and records meaningful changes.

At boot, the platform performs startup checks and can announce whether the robot is ready or requires troubleshooting.

## Command-Line Administration

The `betabox` command provides platform administration and troubleshooting tools.

Common commands include:

```bash
betabox status
betabox doctor
betabox services
betabox events
betabox monitor
betabox logs <service>
betabox restart <service>
betabox urls
betabox version
```

Additional recovery and administration commands are available through the CLI.

For normal classroom use, Launchpad provides browser access to the most important status and diagnostic information.

## Repository Structure

The repository is organized around the major platform layers.

```text
betabox_robotics/
├── audio/
├── calibration/
├── camera/
├── cli/
├── drive/
├── hardware/
├── launchpad/
├── robots/
├── runtime/
├── sensors/
├── services/
├── system/
└── vision/

deployment/
examples/
tests/
```

### `hardware`

Reusable low-level hardware abstractions.

### `drive`, `sensors`, `camera`, `audio`, `vision`, `system`

Reusable robot subsystems.

### `robots`

Robot configuration and composed robot implementations.

### `runtime`

Centralized robot runtime, runtime client, control leases, and runtime protocol.

### `calibration`

Persistent robot calibration models and storage.

### `services`

Platform monitoring, health, diagnostics, verification, boot behavior, and supporting services.

### `launchpad`

Browser-based Betabox user interface and HTTP APIs.

### `cli`

Command-line platform administration.

### `deployment`

Installation, provisioning, systemd configuration, JupyterHub configuration, and other deployment assets.

### `examples`

Example programs demonstrating the public API and individual platform capabilities.

### `tests`

Automated unit and integration tests.

## Supported Platform

The current Betabox platform is developed for the Betabox robotic car using:

- Raspberry Pi
- Raspberry Pi OS Bookworm
- Python 3.11
- Robot HAT
- Raspberry Pi camera with Picamera2
- HiFiBerry audio hardware
- ultrasonic sensor
- three-channel grayscale module
- DC drive motors
- steering servo
- pan/tilt camera servos

The architecture is designed so additional robot implementations can eventually reuse the common hardware, subsystem, runtime, and platform layers.

## Installation

Betabox Robotics is intended to run on a Raspberry Pi using the Betabox deployment tooling included with this repository.

There are several ways to obtain and install the platform depending on whether you are provisioning a new robot, working from an existing Git checkout, or setting up a development environment.

### Bootstrap Installation

For a new Betabox, the preferred installation method is the repository's bootstrap installer.

The bootstrap process is intended to take a Raspberry Pi from a fresh supported Raspberry Pi OS installation to a configured Betabox platform. It obtains the Betabox Robotics repository and runs the deployment process required to configure the robot.

Run the bootstrap script using the project's published bootstrap command:

```bash
curl -fsSL <bootstrap-url> | bash
```

The bootstrap installer is the recommended method for provisioning a new production/classroom robot because it provides a consistent starting point and performs the complete installation workflow.

The bootstrap process installs and configures the components required by the platform, including:

- Betabox Robotics
- the Betabox Python environment
- required operating-system packages
- Python dependencies
- JupyterHub
- the Betabox Jupyter kernel
- Launchpad
- the centralized robot runtime
- the vision service
- platform monitoring
- boot announcements
- Wi-Fi fallback
- hostname configuration
- managed user/workspace support
- systemd services
- required Raspberry Pi hardware interfaces

After installation, reboot the robot:

```bash
sudo reboot
```

Then verify the platform:

```bash
betabox status
```

For a more complete diagnostic check:

```bash
betabox doctor
```

> The bootstrap URL and branch used for production installation should point to the current supported release of the repository.

### Install from Git

The platform can also be installed from a Git checkout.

This is useful when:

- installing from a particular branch
- testing unreleased platform changes
- developing Betabox Robotics
- inspecting or modifying the deployment process before running it

Clone the repository:

```bash
git clone https://github.com/justinbetabox/betabox_robotics.git
cd betabox_robotics
```

For the normal production version, use the `main` branch:

```bash
git switch main
```

To install or test another branch:

```bash
git fetch origin
git switch <branch>
```

The repository's deployment scripts can then be run directly from the checkout.

For example:

```bash
./deployment/install.sh
```

Use the actual deployment entry point and options appropriate for the current installer if they differ.

Installing from Git gives you explicit control over exactly which revision of Betabox Robotics is being installed.

You can confirm the current revision with:

```bash
git status
git branch --show-current
git log -1 --oneline
```

### Install a Specific Revision

For testing or reproducible deployments, a specific tag or commit can be checked out before installation.

For a tag:

```bash
git fetch --tags
git checkout <tag>
```

For a particular commit:

```bash
git checkout <commit>
```

Then run the normal deployment process from that checkout.

This can be useful when comparing platform versions or reproducing an issue on a known software revision.

### Development Installation

For development, clone the repository normally:

```bash
git clone https://github.com/justinbetabox/betabox_robotics.git
cd betabox_robotics
```

Use the project virtual environment configured for the development system.

Betabox Robotics is installed in editable mode during normal development so changes to the repository are immediately reflected in the Python package:

```bash
python -m pip install -e .
```

Development should be performed from a Git branch rather than directly modifying a deployed production checkout without version control.

For example:

```bash
git switch -c feat/my-change
```

Run the tests after making changes:

```bash
python -m unittest discover -s tests
```

Hardware-related changes should also be validated on a real Betabox before being merged.

### Updating an Existing Git Installation

If the robot already contains a Git checkout of Betabox Robotics, inspect it before updating:

```bash
cd /opt/libs/betabox_robotics

git status
git branch --show-current
```

Do not pull over uncommitted local changes unless those changes are intentionally being preserved.

For a clean installation tracking `main`:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
```

If an update changes dependencies, system configuration, services, or deployment assets, pulling the repository alone may not be sufficient. Run the appropriate deployment/update process for that release.

After updating, restart or reboot the platform as required:

```bash
sudo reboot
```

Then verify:

```bash
betabox status
betabox doctor
```

### Installation Verification

A successful installation should result in the core Betabox services starting automatically.

Start with:

```bash
betabox status
```

Check the systemd services directly when necessary:

```bash
systemctl --failed
```

For detailed platform diagnostics:

```bash
betabox doctor
```

Platform events can provide additional information about hardware or service state changes:

```bash
betabox events
```

Individual service logs can be inspected through the Betabox CLI:

```bash
betabox logs <service>
```

or directly through systemd:

```bash
journalctl -u <service> -n 100 --no-pager
```

After installation, Launchpad and JupyterHub should be available through the URLs reported by:

```bash
betabox urls
```

### Fresh Installation vs. Development

For normal classroom robots, prefer:

```text
Fresh Raspberry Pi OS
        ↓
Bootstrap installer
        ↓
Production/main release
        ↓
Reboot
        ↓
betabox status
        ↓
betabox doctor
```

For development and testing, prefer:

```text
Git checkout
        ↓
Feature branch
        ↓
Editable Python installation
        ↓
Automated tests
        ↓
Hardware validation
        ↓
Commit / push
        ↓
Merge to main
```

Keeping these workflows separate helps ensure classroom robots remain reproducible while development can continue safely on feature branches.

## Development

Clone the repository and work inside the project virtual environment.

The package is developed using Python 3.11.

Run the complete test suite with:

```bash
python -m unittest discover -s tests
```

Individual test modules can be run with:

```bash
python -m unittest tests.<package>.<module>
```

The project uses Python's `unittest` framework.

Before committing substantial platform changes, run the complete test suite and test affected hardware functionality on a real Betabox when the change involves physical devices.

## Hardware Testing

Automated tests cannot prove that every physical component works.

Passive checks can verify observable components such as:

- I2C / Robot HAT communication
- battery readings
- grayscale readings
- ultrasonic readings
- camera availability and frames
- service and runtime state

Actuators require active testing:

- motors must be driven
- steering must be moved
- camera servos must be moved
- audio must be played and heard

The platform distinguishes passive health information from active hardware validation for this reason.

## Classroom Operation

A normal classroom workflow is designed to be simple:

```text
Boot robot
    ↓
Platform services start
    ↓
Runtime initializes hardware
    ↓
Boot verification runs
    ↓
Launchpad becomes available
    ↓
Students use Launchpad / Jupyter
    ↓
Robot is reset for the next session
```

The platform is designed for local/offline classroom operation so core robot functionality does not depend on an external Internet connection.

## Project Status

`betabox_robotics` currently targets the Betabox robotic car.

The project includes the major platform layers required for classroom operation:

- reusable hardware abstractions
- reusable robot subsystems
- composed Betabox car implementation
- public Robot API
- centralized robot runtime
- control ownership
- calibration
- vision service
- audio
- platform status and health
- monitoring and events
- diagnostics
- command-line administration
- Launchpad
- deployment and provisioning

Development is ongoing. APIs and internal platform components may continue to evolve as the classroom platform is tested and expanded.

## License

See the repository license for licensing information.
