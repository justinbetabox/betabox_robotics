# Betabox Robotics Deployment

**Status:** Stable Deployment Specification  
**Project:** Betabox Robotics SDK  
**Document:** `deployment.md`

------------------------------------------------------------------------

## Purpose

This document defines the supported deployment process for installing the
Betabox Robotics SDK onto a clean Raspberry Pi OS installation.

The deployment process should produce a reproducible environment suitable
for Betabox development, testing, classroom deployment, and future
production images.

Unless otherwise documented, all Betabox SDK installations should follow
this process.

------------------------------------------------------------------------

## Supported Platform

The deployment process is currently validated on:

- Raspberry Pi OS Bookworm (64-bit)
- Python 3.11
- Raspberry Pi 4
- Robot HAT
- HifiBerry DAC
- Raspberry Pi Camera using Picamera2

Other operating systems or hardware configurations may work but are not
currently supported.

------------------------------------------------------------------------

## Deployment Philosophy

Deployment should be:

- Reproducible
- Automated
- Version-controlled
- Hardware-aware
- Easy for Betabox developers to execute

A freshly imaged Raspberry Pi should be deployable using the repository
without requiring undocumented manual configuration.

------------------------------------------------------------------------

## Deployment Components

The repository contains two deployment utilities.

### Bootstrap

`deployment/bootstrap.sh`

Responsibilities:

- Install Git if required
- Clone or update the SDK repository
- Execute the installer

### Installer

`deployment/install.sh`

Responsibilities:

- Install required Debian packages
- Create the Python virtual environment
- Install Python dependencies
- Install the Betabox Robotics SDK
- Configure required Raspberry Pi settings
- Perform a deployment smoke test

The installer assumes it is executed from an existing SDK repository.

------------------------------------------------------------------------

## Python Environment

The SDK is installed into:

```text
/opt/betabox/venv
```

The virtual environment is created using:

```bash
python3 -m venv --system-site-packages /opt/betabox/venv
```

System site packages are intentionally enabled to reuse Raspberry Pi
specific libraries including:

- Picamera2
- lgpio
- PyAudio
- Debian NumPy

------------------------------------------------------------------------

## Python Dependencies

Runtime dependencies include:

- aiohttp
- aiortc
- gpiozero
- smbus2

OpenCV is intentionally managed by the deployment installer rather than
the package metadata.

The validated configuration is:

```text
opencv-python==4.12.0.88
opencv-python-headless==4.12.0.88
```

OpenCV is installed using:

```bash
pip install --no-deps \
    opencv-python==4.12.0.88 \
    opencv-python-headless==4.12.0.88
```

This preserves the Debian NumPy installation required by Picamera2 and
simplejpeg.

------------------------------------------------------------------------

## Raspberry Pi Configuration

The installer verifies the following configuration in
`/boot/firmware/config.txt`:

```text
dtparam=i2c_arm=on
dtparam=spi=on

dtoverlay=hifiberry-dac
dtoverlay=i2s-mmap
```

A reboot is required after modifying the Raspberry Pi boot
configuration.

------------------------------------------------------------------------

## Audio

The SDK manages the Robot HAT speaker amplifier automatically during
audio playback.

No boot-time GPIO service is required.

------------------------------------------------------------------------

## Repository Layout

Recommended installation:

```text
/opt/
├── betabox/
│   └── venv/
└── libs/
    └── betabox_robotics/
```

User media:

```text
~/media/
├── audio/
├── pictures/
└── videos/
```

------------------------------------------------------------------------

## Deployment Workflow

Typical deployment consists of:

1. Flash Raspberry Pi OS.
2. Clone the Betabox Robotics repository.
3. Execute `deployment/install.sh`.
4. Reboot if required.
5. Activate the virtual environment.
6. Run the verification examples.

------------------------------------------------------------------------

## Fresh Image Installation

### Recommended (Bootstrap)

```bash
curl -fsSL https://raw.githubusercontent.com/justinbetabox/betabox_robotics/main/deployment/bootstrap.sh | bash
```

After installation:

```bash
sudo reboot
```

### Manual Installation

```bash
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

- The SDK imports successfully.
- Hardware initializes correctly.
- Audio functions correctly.
- Camera functions correctly.
- Robot demonstrations execute successfully.
- SDK tests complete without errors.

Typical verification commands:

```bash
source /opt/betabox/venv/bin/activate

python -c "import betabox_robotics; print(betabox_robotics.__version__)"

python -m betabox_robotics.examples.robots.betabox_car.basic_robot_demo

python -m betabox_robotics.examples.subsystems.audio.audio_demo
```

Run the automated tests:

```bash
cd /opt/libs/betabox_robotics

for test in $(find tests -name "test_*.py" | sort); do
    echo "===== $test ====="
    python "$test" || break
done
```

------------------------------------------------------------------------

## Troubleshooting

Common deployment issues include:

- I²C not enabled
- Missing HifiBerry overlays
- Incorrect OpenCV version
- Replaced Debian NumPy installation
- Missing speech backend
- Camera unavailable before reboot
- Missing media assets required by examples

Deployment issues should be resolved by updating the deployment scripts
rather than introducing undocumented manual steps.

------------------------------------------------------------------------

## Deployment Principles

- Deployment should be reproducible.
- Deployment should be automated whenever practical.
- Raspberry Pi specific configuration belongs in deployment tools.
- Python package management should remain separate from platform
  configuration.
- Deployment should avoid undocumented manual steps.
- Every deployment change should be validated on a fresh Raspberry Pi
  image.

------------------------------------------------------------------------

## Long-Term Goal

The deployment system is intended to provide a fully reproducible
installation process for all Betabox robotic platforms.

Future improvements should simplify deployment while preserving
reproducibility and minimizing manual configuration.

------------------------------------------------------------------------

## Summary

The Betabox Robotics deployment system provides a repeatable,
version-controlled process for preparing a Raspberry Pi for SDK
development and classroom use.

Bootstrap handles repository setup while the installer handles system
configuration, Python dependencies, SDK installation, Raspberry Pi
configuration, and deployment verification.
