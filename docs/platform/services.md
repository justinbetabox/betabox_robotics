# Betabox Platform Services

**Status:** Platform Architecture Specification\
**Project:** Betabox Robot Platform\
**Document:** `services.md`

------------------------------------------------------------------------

## Purpose

Platform Services provide the operational capabilities that transform the Betabox Robotics SDK into a complete, classroom-ready robot platform.

Unlike the Robot SDK, which provides programming interfaces for student applications, Platform Services manage deployment, health, diagnostics, recovery, monitoring, and long-running background functionality.

Applications should interact with robots through the Robot API rather than directly controlling Platform Services.

------------------------------------------------------------------------

## Philosophy

Platform Services should:

-    Operate automatically
-    Be safe by default
-    Recover gracefully from failures
-    Minimize classroom interruptions
-    Hide operating-system complexity
-    Remain independent of student applications

------------------------------------------------------------------------

## Service Categories

### Platform Service Modules

The `services/` package provides reusable platform functionality.

Current services include:

  Service                Purpose
  ---------------------- --------------------------------
  `status.py`            Platform status reporting
  `verify.py`            Installation verification
  `doctor.py`            Diagnostic checks
  `monitor.py`           Background health monitoring
  `system_health.py`     Health aggregation
  `hardware_status.py`   Hardware inspection
  `backup.py`            Backup creation
  `restore.py`           Backup restoration
  `reset.py`             Classroom reset
  `snapshot.py`          Diagnostic snapshots
  `logs.py`              Log access
  `events.py`            Event reporting
  `video.py`             Managed vision service support
  `wifi_fallback.py`     Network recovery
  `hostname.py`          Robot identity management
  `managed.py`           Managed resource helpers
  `services.py`          Service management
  `boot_announce.py`     Audible boot status
  `install_check.py`     Installation validation

------------------------------------------------------------------------

### Managed System Services

Deployment configures long-running system services including:

-    betabox-video.service
-    betabox-monitor.service
-    betabox-boot-announce.service
-    wifi-fallback.service
-    set-hostname-from-serial.service
-    jupyterhub.service

These services are installed during deployment and managed by systemd.

------------------------------------------------------------------------

## Platform Architecture

``` text
    Applications
         │
         ▼
     Robot API
         │
         ▼
  Platform Services
         │
         ▼
Managed System Services
         │
         ▼
Linux Operating System
```

The Robot SDK provides robot capabilities while Platform Services provide operational capabilities.

------------------------------------------------------------------------

## Responsibilities

Platform Services are responsible for:

-    Platform health
-    Diagnostics
-    Monitoring
-    Backup and recovery
-    Classroom reset
-    Event reporting
-    Log management
-    Managed video services
-    Network recovery
-    Robot identity
-    Background task coordination

------------------------------------------------------------------------

## Non-Responsibilities

Platform Services are **not** responsible for:

-    Robot movement
-    Sensor acquisition
-    Vision algorithms
-    Audio playback
-    Student applications
-    Curriculum logic

Those responsibilities belong to the SDK and higher-level applications.

------------------------------------------------------------------------

## Service Lifecycle

Typical lifecycle:

``` text
       Boot
         │
         ▼
  Systemd Services
         │
         ▼
Platform Initialization
         │
         ▼
  Health Monitoring
         │
         ▼
    Robot Ready
```

Services continue monitoring and coordinating the platform until shutdown.

------------------------------------------------------------------------

## Interaction with the SDK

``` text
  Applications
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
     Linux
```

Student applications should not invoke operating-system functionality directly.

------------------------------------------------------------------------

## Reliability

Platform Services are designed to:

-    Detect failures
-    Report health
-    Preserve diagnostics
-    Support recovery
-    Operate safely in classroom environments

Where practical, failures should degrade gracefully rather than preventing normal robot operation.

------------------------------------------------------------------------

## Future Expansion

Future Platform Services may include:

-    Automatic updates
-    Fleet management
-    Remote diagnostics
-    Configuration synchronization
-    Telemetry
-    Teacher Portal integration
-    Launchpad integration
-    Classroom analytics

New services should integrate through existing platform interfaces whenever practical.

------------------------------------------------------------------------

## Design Principles

Platform Services follow the Betabox Platform Design Principles:

-    Student First
-    Safe by Default
-    Stable Interfaces
-    Explicit Behavior
-    Single Responsibility
-    Classroom Reliability
-    Test Everything

------------------------------------------------------------------------

## Summary

Platform Services provide the operational foundation of the Betabox Robot Platform.

Working alongside the Betabox Robotics SDK, they manage health, diagnostics, monitoring, deployment, recovery, and background services while keeping operating-system complexity hidden from student applications.

Together, the SDK and Platform Services create a reliable, classroom-ready robotics platform.
