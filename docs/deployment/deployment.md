# Betabox Robot Platform Deployment

**Status:** Stable Deployment Specification\
**Project:** Betabox Robot Platform\
**Document:** `deployment.md`

------------------------------------------------------------------------

## Purpose

This document defines the supported deployment process for installing
the complete Betabox Robot Platform onto a clean Raspberry Pi OS
installation.

Deployment prepares a Raspberry Pi as a classroom-ready robot by
installing the Betabox Robotics SDK, platform services, deployment
assets, administration tools, and required operating-system
configuration.

Unless otherwise documented, all Betabox platform installations should
follow this process.

------------------------------------------------------------------------

## Supported Platform

The deployment process is currently validated on:

-    Raspberry Pi OS Bookworm (64-bit)
-    Python 3.11
-    Raspberry Pi 4
-    Robot HAT
-    HiFiBerry DAC
-    Raspberry Pi Camera using Picamera2

Other operating systems or hardware configurations may work but are not
currently supported.

------------------------------------------------------------------------

## Deployment Philosophy

Deployment should be:

-    Reproducible
-    Automated
-    Version-controlled
-    Hardware-aware
-    Classroom-ready
-    Easy for Betabox developers to execute

A freshly imaged Raspberry Pi should be deployable using the repository
without requiring undocumented manual configuration.

------------------------------------------------------------------------

## Deployment Overview

``` text
  Fresh Raspberry Pi
          │
          ▼
deployment/bootstrap.sh
          │
          ▼
 deployment/install.sh
          │
          ▼
 Platform Configuration
          │
          ▼
   Platform Services
          │
          ▼
 Betabox Robot Platform
```

------------------------------------------------------------------------

## Deployment Components

### Bootstrap

`deployment/bootstrap.sh`

Responsibilities:

-    Install Git if required
-    Clone or update the repository
-    Execute the installer

### Installer

`deployment/install.sh`

Responsibilities:

-    Install required Debian packages
-    Create the Python virtual environment
-    Install Python dependencies
-    Install the Betabox Robotics SDK
-    Configure Raspberry Pi settings
-    Install deployment assets
-    Configure platform services
-    Perform deployment verification

### Platform Services

Deployment installs and configures managed services including:

-    Betabox Video
-    Betabox Monitor
-    Boot Announcer
-    Wi-Fi Fallback
-    JupyterHub
-    Hostname Management

------------------------------------------------------------------------

## Python Environment

The SDK is installed into:

``` text
/opt/betabox/venv
```

Created with:

``` bash
python3 -m venv --system-site-packages /opt/betabox/venv
```

System site packages are intentionally enabled to reuse Raspberry Pi
libraries such as Picamera2, lgpio, PyAudio, and Debian NumPy.

------------------------------------------------------------------------

## Python Dependencies

Runtime dependencies include:

-    aiohttp
-    aiortc
-    gpiozero
-    smbus2

OpenCV is intentionally installed separately from package metadata.

Validated versions:

``` text
opencv-python==4.12.0.88
opencv-python-headless==4.12.0.88
```

Installed with:

``` bash
pip install --no-deps \
    opencv-python==4.12.0.88 \
    opencv-python-headless==4.12.0.88
```

This preserves the Debian NumPy installation required by Picamera2 and
related packages.

------------------------------------------------------------------------

## Raspberry Pi Configuration

The installer verifies the following entries in
`/boot/firmware/config.txt`:

``` text
dtparam=i2c_arm=on
dtparam=spi=on

dtoverlay=hifiberry-dac
dtoverlay=i2s-mmap
```

A reboot is required after modifying boot configuration.

------------------------------------------------------------------------

## Repository Layout

Recommended installation:

``` text
/opt/
├── betabox/
│   └── venv/
├── libs/
│   └── betabox_robotics/
└── betabox-curriculum/
```

User media:

``` text
~/media/
├── sounds/
├── pictures/
└── videos/
```

------------------------------------------------------------------------

## Deployment Workflow

1.  Flash Raspberry Pi OS.
2.  Clone the repository.
3.  Execute `deployment/install.sh`.
4.  Reboot if required.
5.  Activate the virtual environment.
6.  Verify platform services.
7.  Run demonstration programs.

------------------------------------------------------------------------

## Fresh Image Installation

### Bootstrap

``` bash
curl -fsSL https://raw.githubusercontent.com/justinbetabox/betabox_robotics/main/deployment/bootstrap.sh | bash
sudo reboot
```

### Manual Installation

``` bash
sudo apt update
sudo apt install -y git

sudo mkdir -p /opt/libs
sudo chown -R pi:pi /opt/libs

cd /opt/libs
git clone https://github.com/justinbetabox/betabox_robotics.git
cd betabox_robotics

chmod +x deployment/install.sh
./deployment/install.sh
```

------------------------------------------------------------------------

## Verification

Deployment is considered successful when:

-    The SDK imports successfully.
-    Platform services are running.
-    Audio functions correctly.
-    Camera functions correctly.
-    Robot demonstrations execute successfully.
-    Validation tests complete successfully.

Typical verification:

``` bash
source /opt/betabox/venv/bin/activate

python -c "import betabox_robotics; print(betabox_robotics.__version__)"

python -m betabox_robotics.examples.robots.betabox_car.basic_robot_demo
```

For complete testing and validation procedures, see
`docs/development/testing.md`.

------------------------------------------------------------------------

## Troubleshooting

Common deployment issues include:

### Hardware

-    I²C not enabled
-    Missing HiFiBerry overlays
-    Camera unavailable before reboot

### Python

-    Incorrect OpenCV version
-    Replaced Debian NumPy installation
-    Missing speech backend

### Platform

-    Platform services not running
-    Missing media assets
-    Incomplete installation

Deployment issues should be resolved by improving deployment automation
rather than relying on undocumented manual steps.

------------------------------------------------------------------------

## Deployment Principles

-    Deployment should be reproducible.
-    Deployment should be automated whenever practical.
-    Raspberry Pi configuration belongs in deployment tools.
-    Python package management should remain separate from platform configuration.
-    Deployment should avoid undocumented manual steps.
-    Every deployment change should be validated on a fresh Raspberry Pi image.

------------------------------------------------------------------------

## Long-Term Goal

The deployment system is intended to transform a clean Raspberry Pi
installation into a fully configured Betabox Robot Platform with minimal
manual configuration.

Future improvements should simplify deployment while preserving
reproducibility, reliability, and classroom readiness.

------------------------------------------------------------------------

## Summary

The Betabox deployment system provides a repeatable, version-controlled
process for preparing a Raspberry Pi as a complete Betabox robot.

Bootstrap prepares the repository, the installer configures the
operating system and SDK, and managed platform services complete the
installation, resulting in a classroom-ready Betabox Robot Platform.
