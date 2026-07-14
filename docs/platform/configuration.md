# Betabox Platform Configuration

**Status:** Platform Architecture Specification\
**Project:** Betabox Robot Platform\
**Document:** `configuration.md`

------------------------------------------------------------------------

## Purpose

The Betabox Platform Configuration system provides a centralized source
of truth for platform-wide configuration.

Rather than scattering constants throughout services, deployment tools,
and diagnostics, configuration is organized into a single immutable
configuration model that is shared across the platform.

This allows services to remain consistent, easier to maintain, and
simpler to extend as the platform grows.

------------------------------------------------------------------------

## Philosophy

Configuration should describe **the installed platform**, not the robot.

Services should consume configuration rather than defining their own
constants.

Configuration should be:

-    Centralized
-    Explicit
-    Immutable
-    Reusable
-    Easy to override when appropriate

Command-line options may temporarily override configuration values, but
the platform defaults remain defined by `PlatformConfig`.

------------------------------------------------------------------------

## Platform Configuration Overview

``` text
                PlatformConfig
                      │
      ┌───────────────┼────────────────┐
      ▼               ▼                ▼
    Paths          Network         Runtime
      │               │                │
      └───────────────┼────────────────┘
                      ▼
                   Health
                      │
                      ▼
                 Monitoring
                      │
                      ▼
                Verification
                      │
                      ▼
                  Services
```

Each configuration section owns a single area of responsibility.

------------------------------------------------------------------------

## Major Components

### PlatformPathsConfig

Defines filesystem locations used by the platform.

Examples include:

-    State directory
-    Log files
-    Event log
-    Backup directory
-    Snapshot directory
-    Media directories

Services should reference `config.paths` instead of hard-coded paths.

------------------------------------------------------------------------

### PlatformNetworkConfig

Defines networking configuration.

Examples include:

-    Bind host
-    Vision service port
-    Wi-Fi interface
-    Ethernet interface
-    Access Point connection
-    Identity prefix
-    Wi-Fi fallback timing

------------------------------------------------------------------------

### PlatformRuntimeConfig

Defines runtime defaults shared by platform services.

Examples include:

-    Vision frame rate

Future runtime defaults should be added here rather than embedded in
individual services.

------------------------------------------------------------------------

### PlatformHealthConfig

Defines health thresholds shared by monitoring and diagnostics.

Examples include:

-    CPU temperature
-    Memory usage
-    Disk usage

------------------------------------------------------------------------

### PlatformMonitoringConfig

Defines monitoring behavior.

Examples include:

-    Poll interval
-    Event history
-    Default display limits

------------------------------------------------------------------------

### PlatformVerificationConfig

Defines verification settings.

Examples include:

-    I²C configuration
-    Verification timeouts
-    Expected platform resources

------------------------------------------------------------------------

### PlatformServicesConfig

Defines managed platform services.

Examples include:

-    Video service
-    Monitor service
-    JupyterHub
-    Wi-Fi fallback
-    Boot announcer

This eliminates duplicated systemd unit names throughout the platform.

------------------------------------------------------------------------

## Relationship to RobotConfig

A key architectural principle is separating platform configuration from
robot configuration.

### PlatformConfig

Describes the installed Betabox platform.

Examples include:

-    Services
-    Networking
-    Monitoring
-    Recovery
-    Logging
-    Runtime defaults

### RobotConfig

Describes robot hardware.

Examples include:

-    Motors
-    Servos
-    Sensors
-    Vision hardware
-    Audio hardware
-    Battery configuration

Multiple robot types can share one platform while exposing different
hardware configurations.

------------------------------------------------------------------------

## Responsibilities

The Platform Configuration system is responsible for:

-    Providing a single source of truth
-    Defining platform defaults
-    Eliminating duplicated constants
-    Supporting dependency injection
-    Improving maintainability
-    Simplifying service development

------------------------------------------------------------------------

## Non-Responsibilities

Platform Configuration is **not** responsible for:

-    Robot pin mappings
-    Motor calibration
-    Sensor calibration
-    Detection algorithms
-    User interface text
-    Business logic
-    Student applications

These belong to `RobotConfig`, subsystem implementations, or
applications.

------------------------------------------------------------------------

## Design Goals

-    Centralized configuration
-    Immutable configuration objects
-    Explicit service dependencies
-    Minimal duplication
-    Stable platform APIs
-    Straightforward testing
-    Long-term maintainability

------------------------------------------------------------------------

## Future Direction

The Platform Configuration system is intended to grow alongside the
platform while remaining stable.

Future additions may include:

-    Additional runtime defaults
-    Launchpad configuration
-    Teacher Portal configuration
-    Fleet management settings
-    Remote management configuration

New configuration should extend existing sections whenever practical.

------------------------------------------------------------------------

## Summary

The Betabox Platform Configuration system provides the centralized
configuration foundation for the Betabox Platform.

It separates platform configuration from robot hardware configuration,
allowing platform services to evolve independently while preserving a
stable architecture for applications, teachers, students, and future
robot platforms.
