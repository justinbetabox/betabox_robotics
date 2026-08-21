# Betabox Robotics

`betabox_robotics` is the software platform for the Betabox robotic car.

It provides the Python Robot API, centralized robot runtime, hardware and
subsystem abstractions, browser-based Launchpad interface, platform services,
diagnostics, calibration, and deployment tooling used by Betabox classroom
robots.

The platform is designed to provide one consistent interface from physical
robot hardware through student-facing applications.

## Features

- High-level Python Robot API
- Centralized robot runtime and hardware ownership
- Drive, steering, sensors, vision, and audio
- Persistent robot calibration
- Browser-based Betabox Launchpad
- JupyterHub integration
- Manual Drive
- Platform status and diagnostics
- Continuous health monitoring and event history
- Boot verification and announcements
- Offline classroom operation
- Automated Raspberry Pi deployment and provisioning

## Architecture

Betabox Robotics is organized as a layered platform:

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
            ├── Central Robot Runtime
            │       │
            │       ├── Drive
            │       ├── Sensors
            │       └── Camera Mount
            │               │
            │               ▼
            │        Hardware Abstractions
            │
            ├── Vision Service
            │       └── Camera
            │
            ├── Audio
            └── System
```

The central robot runtime owns and coordinates shared drive, sensor, and
camera-mount hardware. Camera capture is shared through the Vision service,
while Audio and System capabilities remain separate platform interfaces.

Applications requiring actuator control acquire a control lease. Supported
read-only operations remain available without taking control of the robot.

See [Platform Architecture](docs/architecture.md) and
[Central Robot Runtime](docs/runtime.md) for the detailed design.

## Python API

The primary student and application interface is `Robot`:

```python
from betabox_robotics import Robot

robot = Robot.default()
```

The high-level API provides access to functionality including:

- driving and steering
- ultrasonic distance
- grayscale sensing
- battery information
- camera snapshots and recording
- vision streaming
- speech and audio
- robot identity and system information

Applications should normally use the Robot API or appropriate shared platform
service rather than constructing robot hardware directly.

## Betabox Launchpad

Launchpad is the browser-based interface for the Betabox platform.

Current functionality includes:

- Manual Drive
- Code / Jupyter
- Vision
- Media
- Calibration
- Status
- Diagnostics
- Services
- Events
- Information and preferences

Launchpad is designed for local classroom operation and does not require an
Internet connection during normal use.

See [Betabox Launchpad](docs/launchpad.md).

## Installation

### Bootstrap installation

For a new Betabox, the recommended installation method is the bootstrap
installer:

```bash
curl -fsSL \
https://raw.githubusercontent.com/justinbetabox/betabox_robotics/main/deployment/bootstrap.sh \
| bash
```

The bootstrap installer obtains the current `main` branch and runs the Betabox
deployment process.

After installation:

```bash
sudo reboot
```

Then verify the platform:

```bash
betabox status
betabox doctor
```

### Install from Git

The platform can also be installed from an explicit Git checkout:

```bash
git clone https://github.com/justinbetabox/betabox_robotics.git
cd betabox_robotics
git switch main

chmod +x deployment/install.sh
./deployment/install.sh
```

Installing from Git is useful for development, testing feature branches, or
installing a specific revision.

For complete installation, update, and verification instructions, see
[Installation](docs/installation.md).

## Command-Line Administration

The `betabox` command provides platform administration and troubleshooting.

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

Launchpad provides browser access to the most important classroom-facing
status and diagnostic functionality.

## Repository Structure

The repository root also serves as the `betabox_robotics` Python package.

```text
.
├── audio/
├── calibration/
├── camera/
├── cli/
├── config/
├── curriculum/
├── deployment/
├── docs/
├── drive/
├── hardware/
├── launchpad/
├── robots/
├── runtime/
├── sensors/
├── services/
├── system/
├── tests/
├── vision/
├── README.md
└── pyproject.toml
```

The major areas are:

- `hardware` — reusable low-level hardware abstractions
- `drive`, `sensors`, `camera`, `audio`, `vision`, `system` — robot subsystems
  and shared platform capabilities
- `robots` — robot configuration and composed robot implementations
- `runtime` — centralized runtime, clients, protocol, and control ownership
- `calibration` — calibration models and persistence
- `services` — health, monitoring, diagnostics, events, accounts, calibration
  hardware operations, and other platform services
- `launchpad` — browser interface and HTTP/WebSocket APIs
- `cli` — command-line administration
- `deployment` — installation, provisioning, systemd, and JupyterHub
  configuration
- `curriculum` — classroom curriculum scaffolding and lesson content under
  development
- `tests` — automated tests, currently focused primarily on the centralized
  runtime

## Documentation

- [Platform Architecture](docs/architecture.md)
- [Central Robot Runtime](docs/runtime.md)
- [Betabox Launchpad](docs/launchpad.md)
- [Installation](docs/installation.md)
- [Development](docs/development.md)
- [Calibration](docs/calibration.md)
- [Platform Health and Diagnostics](docs/platform-health.md)
- [Hardware](docs/hardware.md)

## Supported Platform

The current platform targets the Betabox robotic car using:

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

The architecture is designed so common hardware, subsystem, runtime, and
platform components can be reused by future robot implementations.

## Development

Activate the Betabox environment when developing directly on a robot:

```bash
source /opt/betabox/venv/bin/activate
```

Run the current checked-in automated tests with:

```bash
python -m unittest discover -s tests
```

Hardware-related changes must also be validated on a real Betabox when
automated testing cannot verify physical behavior.

See [Development](docs/development.md) for the complete development workflow.

## Project Status

Betabox Robotics currently provides the major platform layers required for
Betabox car classroom operation, including the Robot API, centralized runtime,
Launchpad, calibration, vision, audio, monitoring, diagnostics, administration,
and deployment.

Development is ongoing as the platform is tested and expanded for classroom
use.

## License

See the repository license for licensing information.
