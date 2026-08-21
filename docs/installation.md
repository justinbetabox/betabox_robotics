# Installation

This guide describes how to install Betabox Robotics on a Betabox robotic car.

For normal classroom robots, the recommended installation method is the
bootstrap installer. Developers can also install directly from a Git checkout
when working with branches or specific revisions.

## Supported Platform

The current Betabox platform targets:

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

A normal installation expects a supported Raspberry Pi OS installation and the
physical Betabox hardware configuration.

## Installation Methods

There are two primary installation workflows:

```text
Production / classroom robot
        ↓
Bootstrap installation

Development / explicit revision
        ↓
Git checkout
        ↓
Deployment installer
```

The bootstrap workflow is preferred when provisioning a fresh robot.

A direct Git checkout is useful when:

- developing Betabox Robotics
- testing a feature branch
- installing a specific revision
- inspecting deployment changes before installation

## Bootstrap Installation

The bootstrap installer is the recommended way to provision a new Betabox.

Run:

```bash
curl -fsSL \
https://raw.githubusercontent.com/justinbetabox/betabox_robotics/main/deployment/bootstrap.sh \
| bash
```

The bootstrap process obtains the current `main` branch and prepares the
Betabox Robotics source checkout under:

```text
/opt/libs/betabox_robotics
```

It then runs the main deployment installer:

```text
deployment/install.sh
```

The bootstrap script is intentionally small. The deployment installer remains
responsible for configuring the actual platform.

## Install from Git

The platform can also be installed from an explicit Git checkout.

Clone the repository:

```bash
git clone https://github.com/justinbetabox/betabox_robotics.git
cd betabox_robotics
```

Use the production branch:

```bash
git switch main
```

Run the installer:

```bash
chmod +x deployment/install.sh
./deployment/install.sh
```

The deployment installer uses `sudo` internally for operations requiring
elevated privileges.

Do not run the entire installer as `root` unless the deployment tooling
explicitly requires it.

## Installing a Feature Branch

For development or hardware testing, a feature branch can be installed
instead of `main`.

Clone the repository if necessary:

```bash
git clone https://github.com/justinbetabox/betabox_robotics.git
cd betabox_robotics
```

Fetch the current remote branches:

```bash
git fetch origin
```

Switch to the desired branch:

```bash
git switch <branch>
```

Confirm the selected branch:

```bash
git branch --show-current
```

Then run:

```bash
./deployment/install.sh
```

Feature branches should be used for development and validation rather than
normal classroom deployments.

## Installing a Specific Revision

A particular commit can be checked out when a reproducible software revision
is required.

```bash
git fetch origin
git checkout <commit>
```

Confirm the revision:

```bash
git log -1 --oneline
```

Then run the normal deployment installer:

```bash
./deployment/install.sh
```

A tag can be used similarly if the repository contains a tagged release:

```bash
git fetch --tags
git checkout <tag>
```

## Installation Layout

The deployment process uses several important filesystem locations.

### Source

The normal Betabox Robotics checkout is:

```text
/opt/libs/betabox_robotics
```

This is the source tree used for platform development and the editable Python
installation.

### Betabox Environment

The main Betabox Python environment is:

```text
/opt/betabox/venv
```

Activate it with:

```bash
source /opt/betabox/venv/bin/activate
```

The `betabox_robotics` package is installed into this environment in editable
mode.

As a result, changes made in:

```text
/opt/libs/betabox_robotics
```

are reflected by Python without reinstalling the package.

### JupyterHub

JupyterHub uses its own environment under:

```text
/opt/jupyterhub/venv
```

Separating the JupyterHub environment from the robot platform environment
keeps the web service dependencies separate from the student Robot API
environment.

## What the Installer Configures

The deployment installer prepares the Raspberry Pi for the complete Betabox
platform.

The installation process includes configuration of areas such as:

- operating-system packages
- Python environments
- Betabox Robotics
- Python dependencies
- Raspberry Pi hardware interfaces
- JupyterHub
- the Betabox Jupyter kernel
- Launchpad
- centralized robot runtime
- vision service
- platform monitoring
- boot announcements
- Wi-Fi fallback
- hostname configuration
- managed users and workspaces
- systemd services
- platform permissions
- deployment assets

The deployment scripts in the repository are authoritative for the exact
packages, files, and service definitions installed by a particular revision.

## Python Environment

The main Betabox environment is created under:

```text
/opt/betabox/venv
```

Development and platform Python commands should normally use this environment.

Activate it with:

```bash
source /opt/betabox/venv/bin/activate
```

Then verify the interpreter:

```bash
which python
python --version
```

Do not create unrelated package installations with the system Python when
working on the deployed platform.

## JupyterHub

The installer configures JupyterHub for student programming.

JupyterHub is kept separate from the main Betabox virtual environment, while
student notebooks use the configured Betabox robot kernel.

This allows notebook code to access the supported Robot API without requiring
students to manage Python environments manually.

After installation, the JupyterHub service should start automatically with
the platform.

## Platform Services

Betabox uses systemd to run long-lived platform components.

These include services responsible for areas such as:

- robot runtime
- Launchpad
- vision
- monitoring
- boot announcements
- JupyterHub
- Wi-Fi fallback
- hostname configuration
- guest workspace management

The exact service set is defined by the current platform configuration and
deployment assets.

Inspect platform services with:

```bash
betabox services
```

Systemd can also be queried directly:

```bash
systemctl --failed
```

## Raspberry Pi Hardware Configuration

The deployment process configures the Raspberry Pi interfaces required by the
Betabox hardware.

These include interfaces used for:

- I2C
- SPI
- audio
- camera support
- Robot HAT communication

The installer also applies the required boot configuration for supported
Betabox hardware.

Because some of these settings are applied during boot, a reboot is required
after initial installation.

## Reboot

After a fresh installation:

```bash
sudo reboot
```

Allow the Raspberry Pi to complete its normal startup sequence before
performing verification.

The platform services should start automatically.

## Installation Verification

After reboot, begin with:

```bash
betabox status
```

This provides an overview of platform state.

For a more detailed verification:

```bash
betabox doctor
```

Also check for failed systemd services:

```bash
systemctl --failed
```

The platform URLs can be displayed with:

```bash
betabox urls
```

Platform events can provide additional information:

```bash
betabox events
```

## Runtime Verification

A successful installation should result in the centralized robot runtime
starting and reaching a usable state.

Status and diagnostics should indicate whether:

- the runtime service is available
- hardware ownership was acquired
- robot hardware initialized
- observable sensors are available
- supporting platform services are running

A running service alone does not prove that every physical component works.

See [Platform Health and Diagnostics](platform-health.md) for the distinction
between passive health checks and active hardware testing.

## Launchpad Verification

After installation, open the Launchpad URL reported by:

```bash
betabox urls
```

Verify that Launchpad loads and that its status information agrees with:

```bash
betabox status
```

Useful initial checks include:

- Status
- Diagnostics
- Services
- Events
- Calibration
- Manual Drive

Hardware-affecting pages should only be tested when the robot is positioned
safely.

## JupyterHub Verification

Open the JupyterHub URL reported by:

```bash
betabox urls
```

Start a notebook using the configured Betabox robot kernel.

A basic API import can be checked with:

```python
from betabox_robotics import Robot

robot = Robot.default()
```

Physical robot commands should only be run when the robot can move safely.

## Hardware Verification

Some hardware can be checked passively after installation.

Observable hardware includes:

- Robot HAT / I2C communication
- battery
- grayscale sensor
- ultrasonic sensor
- camera / vision state

Other hardware requires active testing.

Examples include:

- drive motors
- steering servo
- camera pan/tilt servos
- audible speaker output

Do not interpret successful runtime initialization as proof that every
physical actuator works.

## Checking Logs

The Betabox CLI can display logs for managed services:

```bash
betabox logs <service>
```

Systemd logs can also be inspected directly:

```bash
journalctl -u <service> -n 100 --no-pager
```

For live systemd output:

```bash
journalctl -u <service> -f
```

Platform events are available with:

```bash
betabox events
```

Events are particularly useful for hardware or service failures that occurred
earlier but have since recovered.

## Updating an Existing Installation

Before updating a robot, inspect the current checkout:

```bash
cd /opt/libs/betabox_robotics

git status
git branch --show-current
git log -1 --oneline
```

Do not overwrite uncommitted work accidentally.

For a clean checkout tracking `main`:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
```

Confirm the result:

```bash
git status
git log -1 --oneline
```

## Deployment Changes During Updates

A Git pull updates the source tree but does not necessarily apply every
deployment change.

A release may change:

- Python dependencies
- operating-system packages
- systemd units
- sudoers rules
- JupyterHub configuration
- platform assets
- users or groups
- Raspberry Pi boot configuration

When deployment files have changed, run the appropriate deployment installer
for that revision rather than assuming a Git pull is sufficient.

For the current deployment workflow:

```bash
./deployment/install.sh
```

Reboot when required:

```bash
sudo reboot
```

Then verify:

```bash
betabox status
betabox doctor
```

## Development Updates

Development robots may intentionally track a feature branch.

Before changing branches:

```bash
git status
```

Commit, stash, or intentionally discard local changes before switching.

Then:

```bash
git fetch origin
git switch <branch>
git pull --ff-only
```

After changing branches, inspect deployment changes before assuming that a
service restart alone is sufficient.

## Service Restarts

For source changes that do not require a complete reinstall or reboot, the
affected service may be restarted.

Use the Betabox CLI when the service is managed there:

```bash
betabox restart <service>
```

Or use systemd directly when appropriate:

```bash
sudo systemctl restart <service>
```

Check its state afterward:

```bash
systemctl status <service>
```

Not every code change requires reinstalling the entire robot.

Likewise, not every deployment change can be applied with only a service
restart.

## Troubleshooting Installation

Start with:

```bash
betabox status
betabox doctor
systemctl --failed
```

Then inspect:

```bash
betabox events
```

If a particular service is failing:

```bash
betabox logs <service>
```

or:

```bash
journalctl -u <service> -n 100 --no-pager
```

The important distinction is whether the problem is:

- installation/configuration
- service startup
- runtime initialization
- physical hardware
- networking
- application behavior

`betabox doctor` is intended to help make that distinction.

## Clean Installation Workflow

For a normal classroom robot, the preferred workflow is:

```text
Fresh supported Raspberry Pi OS
              ↓
     Bootstrap installer
              ↓
       Deployment installer
              ↓
             Reboot
              ↓
        Platform startup
              ↓
        betabox status
              ↓
        betabox doctor
              ↓
       Launchpad verification
              ↓
       Hardware validation
```

This is the preferred path for creating a reproducible classroom Betabox.

## Development Workflow

For development:

```text
Existing development robot
           ↓
     Git feature branch
           ↓
       Source changes
           ↓
      Automated tests
           ↓
     Restart affected
        services
           ↓
     Hardware validation
           ↓
       Commit / push
           ↓
         Merge
           ↓
 Return deployment to main
```

Development branches should not accidentally become the permanent deployment
source for classroom robots.

## Bootstrap vs. Git Installation

Use the bootstrap installer when:

- provisioning a new Betabox
- creating a normal classroom installation
- you want the standard `main` deployment

Use a Git checkout when:

- developing the platform
- testing a branch
- reproducing a particular revision
- inspecting deployment changes manually

Both workflows ultimately use the repository's deployment tooling.

## Source of Truth

Installation behavior is ultimately defined by:

```text
deployment/bootstrap.sh
deployment/install.sh
deployment/
```

This document explains the supported workflow, but deployment scripts remain
authoritative for the exact operations performed by a particular software
revision.

When changing deployment behavior, update both the deployment implementation
and this document in the same change.

## Related Documentation

- [Platform Architecture](architecture.md)
- [Central Robot Runtime](runtime.md)
- [Betabox Launchpad](launchpad.md)
- [Platform Health and Diagnostics](platform-health.md)
- [Hardware](hardware.md)
- [Development](development.md)
