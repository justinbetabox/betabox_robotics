# Betabox Platform Roadmap

**Status:** Active Development Roadmap\
**Project:** Betabox Robot Platform\
**Document:** `roadmap.md`

------------------------------------------------------------------------

## Vision

The Betabox Platform is being developed as a complete educational robotics platform rather than simply a Python SDK.

Development is organized into major milestones that build upon one another while preserving a stable, student-friendly Robot API.

------------------------------------------------------------------------

# Phase 1 --- Foundation ✅

Core platform architecture and reusable SDK.

## Hardware

-    [x] Hardware abstractions
-    [x] GPIO, I²C, PWM, ADC
-    [x] Motor and Servo abstractions
-    [x] Hardware validation

## Reusable Subsystems

-    [x] Drive
-    [x] Sensors
-    [x] Vision
-    [x] Audio
-    [x] System

## Documentation

-    [x] Architecture
-    [x] Design Principles
-    [x] Public API
-    [x] Subsystem documentation

------------------------------------------------------------------------

# Phase 2 --- Stable Robot Platform ✅

A stable Robot API built from reusable subsystem implementations.

## Robot API

-    [x] Stable Robot API
-    [x] Robot hierarchy
-    [x] Robot implementations
-    [x] Convenience APIs
-    [x] Context manager support
-    [x] Resource ownership
-    [x] Health reporting
-    [x] Robot configuration model

## Vision Platform

-    [x] Shared frame pipeline
-    [x] Snapshots
-    [x] Recording
-    [x] WebRTC streaming
-    [x] Metadata bus
-    [x] Overlay rendering
-    [x] Color detection
-    [x] Face detection
-    [ ] Classroom object detection models

## Deployment

-    [x] Bootstrap installer
-    [x] Platform installer
-    [x] Deployment automation
-    [x] System service installation
-    [x] JupyterHub integration
-    [x] Deployment verification

## Validation

-    [x] Hardware validation
-    [x] Subsystem validation
-    [x] Robot validation
-    [x] Developer examples

------------------------------------------------------------------------

# Phase 3 --- Platform Services 🚧

Current development focus.

## Configuration

-    [ ] Configuration audit
-    [ ] Unified configuration model
-    [ ] Configuration validation
-    [ ] Configuration serialization

## Platform Services

-    [x] Backup
-    [x] Restore
-    [x] Reset
-    [x] Monitoring
-    [x] Diagnostics
-    [x] Logging
-    [x] Service management
-    [ ] Software updates

## Platform Health

-    [ ] Aggregated health reporting
-    [ ] Runtime diagnostics
-    [ ] Configuration inspection

------------------------------------------------------------------------

# Phase 4 --- Launchpad

Browser-based platform management.

-    [ ] Dashboard
-    [ ] Robot status
-    [ ] Live video
-    [ ] Diagnostics
-    [ ] Monitoring
-    [ ] Backup and restore
-    [ ] Logs
-    [ ] Configuration management

------------------------------------------------------------------------

# Phase 5 --- Classroom Platform

Educational experience built on the Robot API.

## Teacher Experience

-    [ ] Teacher Portal
-    [ ] Classroom management
-    [ ] Fleet management
-    [ ] Classroom diagnostics

## Student Experience

-    [ ] Student Portal
-    [ ] Curriculum integration
-    [ ] Coding environment
-    [ ] Guided lessons

------------------------------------------------------------------------

# Phase 6 --- Additional Robot Platforms

Reusable subsystem architecture enables additional robots.

-    [ ] Betabox Arm
-    [ ] Betabox Tank
-    [ ] Betabox Rover
-    [ ] Betabox Drone

------------------------------------------------------------------------

# Future Vision Capabilities

-    [ ] Classroom object detection
-    [ ] Traffic sign detection
-    [ ] QR code detection
-    [ ] AprilTags
-    [ ] Pose estimation
-    [ ] OCR
-    [ ] AI acceleration

------------------------------------------------------------------------

# Platform 1.0

Version 1.0 represents a stable educational robotics platform with:

-    Stable Robot API
-    Stable platform services
-    Launchpad
-    Teacher and Student experiences
-    Complete deployment automation
-    Comprehensive documentation
-    Validated classroom workflows
-    Support for multiple Betabox robot platforms

------------------------------------------------------------------------

## Guiding Principles

Throughout development the platform will continue to prioritize:

-    Student-first APIs
-    Hardware independence
-    Reusable subsystem implementations
-    Stable public interfaces
-    Safe operation
-    Classroom reliability
-    Long-term maintainability

------------------------------------------------------------------------

## Summary

The Betabox roadmap emphasizes long-term architectural milestones rather than individual implementation tasks.

Each phase builds upon the previous one while preserving a stable Robot API and enabling the platform to evolve from a reusable robotics SDK into a complete classroom robotics platform.
