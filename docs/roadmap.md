# Betabox Platform Roadmap

------------------------------------------------------------------------

## Foundation

-    [x] Hardware
-    [x] Drive
-    [x] Sensors

------------------------------------------------------------------------

## Core Robot Services

### Vision

-    [x] Foundation
-    [x] Snapshots
-    [x] Recording
-    [ ] Detection
    -    [x] Framework
    -    [x] Color
    -    [x] Face
    -    [ ] Object
        -    [ ] Evaluate object detection inference backends
        -    [ ] Select long-term inference runtime
        -    [ ] Build Betabox object detection dataset
        -    [ ] Train first classroom object detection model
        -    [ ] Integrate custom object detection runtime
        -    [ ] Add validation tests
        -    [ ] Add developer example
        -    [ ] Update public API documentation
    -    [ ] Traffic Sign
        -    [ ] Collect U.S. traffic sign dataset
        -    [ ] Train Betabox traffic sign model
        -    [ ] Integrate traffic sign detector
        -    [ ] Add validation tests
        -    [ ] Add developer example
        -    [ ] Update public API documentation
-    [ ] Configuration
-    [x] Public Vision API

### Audio

-    [x] Foundation

### System

-    [x] Foundation
-    [x] Status
-    [x] Health foundation
-    [ ] Platform health aggregation
-    [ ] Network
-    [ ] Storage
-    [ ] Identity
-    [ ] Services
-    [ ] Diagnostics

------------------------------------------------------------------------
## Robot Platform

### Robot Architecture

-    [x] Robot hardware configuration model
-    [x] Dependency injection into reusable subsystems
-    [x] Robot-specific platform wiring
-    [ ] Shared Robot base class
-    [ ] Public Robot API
-    [ ] Robot lifecycle management
-    [ ] Robot health reporting
-    [ ] Subsystem factory pattern (.default())
-    [ ] Robot composition framework
-    [ ] Robot capability discovery

### Robot Configuration

-    [x] Drive configuration
-    [x] Sensor configuration
-    [ ] Vision configuration
-    [ ] Audio configuration
-    [ ] System configuration
-    [ ] Unified RobotConfig
-    [ ] Configuration validation
-    [ ] Configuration serialization

### Resource Management

-    [ ] Shared resource ownership
-    [ ] Camera ownership
-    [ ] Audio ownership
-    [ ] Graceful subsystem shutdown
-    [ ] Context manager support
-    [ ] Vision lifecycle
-    [ ] Audio lifecycle
-    [ ] System lifecycle

### Robot Implementations

-    [x] Betabox Car
-    [ ] Betabox Arm
-    [ ] Betabox Tank
-    [ ] Betabox Rover
-    [ ] Betabox Drone

### Applications

-    [ ] Portal
-    [ ] Curriculum
-    [ ] Teacher Tools

------------------------------------------------------------------------

## Platform Deployment

-    [ ] Fresh Raspberry Pi setup script
-    [ ] System dependencies
-    [ ] Service files
-    [ ] Camera/audio/I2C configuration
-    [ ] Jupyter kernel setup
-    [ ] Media directory setup
-    [ ] Verification command
-    [ ] Reset and Recovery tools

------------------------------------------------------------------------

## Platform Administration

-    [ ] Backup
-    [ ] Restore
-    [ ] Reset
-    [ ] Monitoring
-    [ ] Logging
-    [ ] Diagnostics CLI
-    [ ] Service Management
-    [ ] Software Updates

------------------------------------------------------------------------

## Documentation

-    [x] Design Principles
-    [x] Platform Architecture
-    [x] Public API
-    [x] Hardware Architecture
-    [x] Drive Architecture
-    [x] Vision Architecture
-    [x] Audio Architecture
-    [x] System Architecture
-    [x] Sensors Architecture
-    [ ] Deployment Guide

------------------------------------------------------------------------

## Validation

### Hardware

-    [x] Hardware validation framework
-    [ ] Complete validation coverage

### Subsystems

-    [ ] Drive validation
-    [ ] Sensors validation
-    [ ] Vision validation
-    [ ] Audio validation
-    [ ] System validation

### Robot

-    [ ] Robot integration validation

### Examples

-    [ ] Hardware examples
-    [ ] Drive examples
-    [ ] Sensors examples
-    [ ] Vision examples
-    [ ] Audio examples
-    [ ] System examples

------------------------------------------------------------------------

## Release Milestones

-    [x] 0.1 Project Initialization
-    [x] 0.2 Hardware Foundation
-    [x] 0.3 Drive & Sensors
-    [x] 0.4 Vision Foundation
-    [ ] 0.5 Vision Capabilities
-    [x] 0.6 Audio Foundation
-    [ ] 0.7 System Services
-    [ ] 0.8 Robot Platform
-    [ ] 0.9 Applications
-    [ ] 1.0 Betabox Platform

------------------------------------------------------------------------

## Architectural Direction

Subsystems (Drive, Sensors, Vision, Audio, and System) are designed to be
robot-independent.

Robot-specific classes are responsible for wiring subsystem implementations
using RobotConfig. Future robot platforms (Arm, Tank, Drone, etc.) should
reuse existing subsystems whenever practical rather than introducing
robot-specific subsystem implementations.

Future robot platforms should compose existing subsystem implementations
through robot-specific configuration rather than modifying reusable
subsystems.

Dependencies should always flow from Robot implementations toward
reusable subsystem implementations and never in the opposite direction.
