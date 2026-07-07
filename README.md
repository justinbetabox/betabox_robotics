# Betabox Robotics

A modern robotics SDK for Raspberry Pi designed for education.

Betabox Robotics provides reusable hardware abstractions, modular robot
subsystems, and a stable Robot API for building classroom robotics
applications.

The SDK is designed around composition, clean architecture, and
hardware-independent programming, allowing robot implementations to
evolve while preserving a consistent programming interface.

---

## Features

- Stable Robot API
- Modular subsystem architecture
- Hardware abstractions for Raspberry Pi robotics
- Vision subsystem with WebRTC streaming
- Audio subsystem with speech and sound playback
- Drive subsystem for motors and steering
- Sensor subsystem for ultrasonic, grayscale, and future sensors
- System utilities and resource management
- Designed for reusable robot platforms

---

## Supported Hardware

Currently validated on:

- Raspberry Pi OS Bookworm (64-bit)
- Raspberry Pi 4
- Python 3.11
- Robot HAT
- HifiBerry DAC
- Raspberry Pi Camera using Picamera2

---

## Quick Start

Clone the repository:

```bash
git clone https://github.com/justinbetabox/betabox_robotics.git

cd betabox_robotics
```

Run the installer:

```bash
chmod +x deployment/install.sh

./deployment/install.sh
```

Reboot:

```bash
sudo reboot
```

Activate the SDK:

```bash
source /opt/betabox/venv/bin/activate
```

Run a demonstration:

```bash
python -m betabox_robotics.examples.robots.betabox_car.basic_robot_demo
```

---

## Repository Layout

```text
betabox_robotics/
├── betabox_robotics/      SDK source
├── docs/                  Documentation
├── examples/              Example programs
├── tests/                 Validation tests
├── deployment/            Installation tools
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Documentation

The documentation is organized by subsystem.

| Document | Description |
|----------|-------------|
| `deployment.md` | Deployment specification |
| `architecture.md` | Platform architecture |
| `design_principles.md` | Core design philosophy |
| `hardware.md` | Hardware abstraction layer |
| `drive.md` | Drive subsystem |
| `vision.md` | Vision subsystem |
| `audio.md` | Audio subsystem |
| `sensors.md` | Sensors subsystem |
| `system.md` | System subsystem |
| `api.md` | Public Robot API |

---

## Project Architecture

The SDK is organized into layered components.

```text
Applications
      │
      ▼
 Robot API
      │
      ▼
Robot Implementations
      │
      ▼
Reusable Subsystems
      │
      ▼
Hardware Abstractions
      │
      ▼
Linux / Device Drivers
```

Applications interact exclusively with the Robot API while internal
implementations remain replaceable.

---

## Installation

The recommended installation process is documented in:

```text
docs/deployment.md
```

The deployment system installs:

- System packages
- Python virtual environment
- SDK dependencies
- Raspberry Pi configuration
- Betabox Robotics SDK

---

## Development

After activating the virtual environment:

```bash
source /opt/betabox/venv/bin/activate
```

Run examples:

```bash
python -m betabox_robotics.examples.robots.betabox_car.basic_robot_demo
```

Run validation tests:

```bash
cd tests

python test_*.py
```

---

## Project Status

Current status:

- Stable deployment process
- Stable platform architecture
- Stable hardware abstractions
- Active SDK development

---

## License

MIT License
