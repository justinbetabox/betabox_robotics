# Betabox Platform

**Status:** Platform Architecture Specification\
**Project:** Betabox Robot Platform\
**Document:** `platform.md`

------------------------------------------------------------------------

## Purpose

The Betabox Platform is the complete software environment that powers a
Betabox robot.

It combines the Betabox Robotics SDK, platform services, deployment
infrastructure, administration tools, and future user interfaces into a
cohesive system designed for education.

Students interact with robots through simple programming interfaces
while the platform manages hardware, services, diagnostics, and recovery
behind the scenes.

------------------------------------------------------------------------

## Philosophy

The Betabox Platform is designed so the robot behaves like an appliance
rather than a collection of independent software packages.

Applications should focus on robot capabilities:

``` python
car.forward()
car.capture()
car.say("Hello")
```

Applications should not need to understand:

-    Linux
-    systemd
-    GPIO
-    Camera drivers
-    Speech engines
-    Network configuration
-    Background services

The platform hides these implementation details while providing a stable
programming experience.

------------------------------------------------------------------------

## Platform Overview

The platform consists of several major layers.

``` text
       Applications
            │
            ▼
Launchpad / CLI / Curriculum
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

Each layer builds on the services provided by the layer beneath it.

------------------------------------------------------------------------

## Major Components

### Betabox Robotics SDK

The SDK provides the public programming interface used by curriculum,
notebooks, and applications.

Major SDK components include:

-    Hardware abstractions
-    Reusable subsystems
-    Robot implementations
-    Stable Robot API

------------------------------------------------------------------------

### Platform Services

Platform services provide capabilities shared across the entire robot.

Examples include:

-    Health monitoring
-    Robot status
-    Diagnostics
-    Verification
-    Backup
-    Restore
-    Reset
-    Event logging
-    Video management
-    Wi-Fi fallback
-    Boot announcements

These services operate behind the Robot API and coordinate platform
behavior.

------------------------------------------------------------------------

### Administration

The Betabox command-line interface provides administration and
maintenance tools.

Examples include:

-    Robot status
-    Diagnostics
-    Service management
-    Backup and restore
-    Reset
-    Logs
-    Monitoring
-    Events

These tools are intended for teachers, administrators, and developers
rather than student applications.

------------------------------------------------------------------------

### Deployment

Deployment prepares a Raspberry Pi to operate as a complete Betabox
robot.

Deployment includes:

-    Platform installation
-    Bootstrap configuration
-    Systemd services
-    JupyterHub configuration
-    Media assets
-    Platform initialization

------------------------------------------------------------------------

### Curriculum

Curriculum, notebooks, and classroom examples build upon the Robot API.

They should remain independent of hardware implementation details and
platform services.

------------------------------------------------------------------------

### Future Launchpad

Launchpad will provide a browser-based interface for interacting with
the platform.

Planned capabilities include:

-    Robot status
-    Live video
-    Diagnostics
-    Monitoring
-    Service management
-    Backup and restore
-    Logs
-    Configuration

------------------------------------------------------------------------

## Responsibilities

The Betabox Platform is responsible for:

-    Providing a stable Robot API
-    Managing platform services
-    Coordinating hardware ownership
-    Monitoring platform health
-    Supporting diagnostics and recovery
-    Managing deployment
-    Providing administration tools
-    Supporting classroom operation

------------------------------------------------------------------------

## Non-Responsibilities

The Betabox Platform is **not** responsible for:

-    Student algorithms
-    Lesson content
-    Classroom curriculum
-    User-created notebooks
-    Application-specific behavior

These are built on top of the platform.

------------------------------------------------------------------------

## Relationship Between Components

``` text
                Applications
                      │
                      ▼
          Robot API / Launchpad / CLI
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
 Betabox Robotics SDK      Platform Services
        │                           │
        └─────────────┬─────────────┘
                      ▼
                    Linux
```

The SDK provides robot capabilities.

Platform Services provide operational capabilities.

Together they form the Betabox Platform.

------------------------------------------------------------------------

## Design Goals

-    Stable public programming interface
-    Hardware independence
-    Managed platform services
-    Safe operation
-    Modular architecture
-    Classroom reliability
-    Straightforward deployment
-    Long-term maintainability

------------------------------------------------------------------------

## Future Direction

The Betabox Platform is intended to evolve into a complete robotics
operating environment.

Future capabilities include:

-    Launchpad
-    Teacher Portal
-    Student Portal
-    Remote management
-    Expanded diagnostics
-    Additional robot platforms
-    AI-assisted tools
-    Fleet management

These additions should build upon the existing platform architecture
without requiring changes to student applications.

------------------------------------------------------------------------

## Summary

The Betabox Platform is the complete software stack that transforms a
Raspberry Pi into a classroom-ready educational robot.

It combines the Betabox Robotics SDK, platform services, deployment
infrastructure, administration tools, and future user interfaces into a
unified system.

This separation allows the platform to evolve internally while
preserving a stable, beginner-friendly programming experience for
students, teachers, and developers.
