# Betabox Robotics

**A Modern Educational Robotics Platform for Raspberry Pi**

Betabox Robotics is a complete educational robotics platform that
combines a stable Python SDK, reusable robot subsystems, deployment
tools, platform services, diagnostics, and classroom infrastructure into
a cohesive robotics environment.

Students and teachers program robots through a simple,
hardware-independent Robot API while the platform manages hardware,
operating-system services, deployment, monitoring, and recovery behind
the scenes.

------------------------------------------------------------------------

## Philosophy

The Betabox Platform is built around a few core principles:

-    Student First
-    Stable Public APIs
-    Hardware Independence
-    Composition over Inheritance
-    Offline-First Classroom Operation
-    Safe by Default
-    Classroom Reliability

Applications should focus on robot capabilities:

``` python
from betabox_robotics import BetaboxCar

with BetaboxCar() as car:
    car.forward(40)
    car.say("Hello")
    photo = car.capture()
```

Applications should not need to understand Linux, systemd, GPIO, camera
drivers, speech engines, or background services.

------------------------------------------------------------------------

## Features

-    Stable Robot API
-    Reusable subsystem architecture
-    Hardware abstraction layer
-    Vision subsystem with snapshots, recording, detection, and WebRTC
    streaming
-    Audio subsystem with speech, sounds, tones, and melodies
-    Drive subsystem with steering and motor control
-    Sensors subsystem with ultrasonic, grayscale, and battery monitoring
-    System subsystem for platform information and health
-    Managed platform services
-    Deployment and classroom management tools

------------------------------------------------------------------------

## Supported Hardware

Currently validated on:

-    Raspberry Pi OS Bookworm (64-bit)
-    Raspberry Pi 4
-    Python 3.11
-    Robot HAT
-    HiFiBerry DAC
-    Raspberry Pi Camera using Picamera2

------------------------------------------------------------------------

## Quick Start

Clone the repository:

``` bash
git clone https://github.com/justinbetabox/betabox_robotics.git
cd betabox_robotics
```

Install:

``` bash
chmod +x deployment/install.sh
./deployment/install.sh
sudo reboot
```

Activate the virtual environment:

``` bash
source /opt/betabox/venv/bin/activate
```

Run a demonstration:

``` bash
python -m betabox_robotics.examples.robots.betabox_car.basic_robot_demo
```

------------------------------------------------------------------------

## Repository Layout

``` text
betabox_robotics/
├── audio/          Audio subsystem
├── cli/            Administration CLI
├── deployment/     Installation and system configuration
├── docs/           Documentation
├── drive/          Drive subsystem
├── examples/       Example programs
├── hardware/       Hardware abstractions
├── robots/         Robot implementations
├── sensors/        Sensors subsystem
├── services/       Platform services
├── system/         System subsystem
├── tests/          Validation and test suite
├── vision/         Vision subsystem
├── README.md
├── pyproject.toml
└── requirements.txt
```

------------------------------------------------------------------------

## Documentation

### Architecture

-    `docs/architecture.md`
-    `docs/design_principles.md`

### SDK

-    `docs/sdk/api.md`
-    `docs/sdk/hardware.md`
-    `docs/sdk/drive.md`
-    `docs/sdk/sensors.md`
-    `docs/sdk/vision.md`
-    `docs/sdk/audio.md`
-    `docs/sdk/system.md`

### Platform

-    `docs/platform/platform.md`
-    `docs/platform/services.md`
-    `docs/platform/administration.md`
-    `docs/platform/configuration.md`
-    `docs/platform/health.md`
-    `docs/platform/recovery.md`
-    `docs/platform/events.md`

### Deployment

-    `docs/deployment/deployment.md`
-    `docs/deployment/fresh_install.md`
-    `docs/deployment/systemd.md`
-    `docs/deployment/jupyterhub.md`

### Development

-    `docs/development/testing.md`
-    `docs/development/validation.md`
-    `docs/development/examples.md`
-    `docs/development/contributing.md`

See `docs/roadmap.md` for the long-term project direction.

------------------------------------------------------------------------

## Platform Architecture

``` text
Applications
       │
       ▼
Launchpad / CLI
       │
       ▼
Robot API
       │
       ▼
Betabox Robotics SDK
       │
       ▼
Platform Services
       │
       ▼
Linux Operating System
```

------------------------------------------------------------------------

## Development

After activating the virtual environment:

``` bash
source /opt/betabox/venv/bin/activate
```

Run an example:

``` bash
python -m betabox_robotics.examples.robots.betabox_car.basic_robot_demo
```

See `docs/development/testing.md` for validation and testing
instructions.

------------------------------------------------------------------------

## Project Status

Current status:

-    Stable SDK architecture
-    Stable subsystem architecture
-    Stable deployment process
-    Active platform development
-    Preparing for Launchpad and future robot platforms

Future robot implementations include:

-    Betabox Car (current)
-    Betabox Arm
-    Betabox Tank
-    Betabox Drone

------------------------------------------------------------------------

## License

MIT License

------------------------------------------------------------------------

Betabox Robotics is designed so students can focus on programming robots
while the platform manages hardware, operating-system services,
deployment, and diagnostics behind the scenes.
