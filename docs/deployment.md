# Betabox Robotics Deployment

## Overview

This document describes the validated installation process for deploying
the Betabox Robotics SDK onto a clean Raspberry Pi OS installation.

This process has been tested on a fresh Raspberry Pi image and
represents the current supported deployment method.

------------------------------------------------------------------------

# Supported Platform

-   Raspberry Pi OS Bookworm (64-bit)
-   Python 3.11
-   Raspberry Pi 4
-   Robot HAT
-   HifiBerry DAC
-   Raspberry Pi Camera using Picamera2

------------------------------------------------------------------------

# System Requirements

The installer installs the required Debian packages:

``` text
git
python3-pip
python3-venv
python3-dev
build-essential
i2c-tools
python3-pyaudio
portaudio19-dev
python3-opencv
python3-picamera2
python3-lgpio
espeak-ng
libttspico-utils
ffmpeg
```

# Python Environment

Create the virtual environment using:

``` bash
python3 -m venv --system-site-packages /opt/betabox/venv
```

# Python Dependencies

``` text
aiohttp
aiortc
smbus2
gpiozero
opencv-python==4.12.0.88
opencv-python-headless==4.12.0.88
```

Install OpenCV with:

``` bash
pip install --no-deps opencv-python==4.12.0.88 opencv-python-headless==4.12.0.88
```

# Raspberry Pi Configuration

Ensure `/boot/firmware/config.txt` contains:

``` text
dtparam=i2c_arm=on
dtparam=spi=on
dtoverlay=hifiberry-dac
dtoverlay=i2s-mmap
```

Reboot after changes.

# Directory Layout

``` text
/opt/betabox/venv
/opt/libs/betabox_robotics
~/media/audio
~/media/pictures
~/media/videos
```

# Audio

The SDK controls the speaker amplifier during playback. No boot-time
GPIO service is required.

Verify HifiBerry:

``` bash
aplay -l
```

# Installation

``` bash
deployment/install.sh
```

# Verification

``` bash
source /opt/betabox/venv/bin/activate
PYTHONPATH=/opt/libs python -c "import betabox_robotics; print(betabox_robotics.__version__)"
PYTHONPATH=/opt/libs python -m betabox_robotics.examples.robots.betabox_car.basic_robot_demo
PYTHONPATH=/opt/libs python -m betabox_robotics.examples.subsystems.audio.audio_demo
```

# Troubleshooting

-   Enable I²C if `/dev/i2c-1` is missing.
-   Activate the virtual environment before running the SDK.
-   Keep OpenCV pinned to 4.12.0.88 and install with `--no-deps`.
-   Verify HifiBerry overlays and `aplay -l` if audio is silent.

# Future Improvements

-   pyproject.toml
-   pip install support
-   Automated verification
-   Hardware diagnostics
