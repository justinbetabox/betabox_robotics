# CHANGELOG

All notable changes to the Betabox Robot Platform are documented in this
file.

The project is currently under active development. Version numbers
represent architectural milestones rather than production releases.

------------------------------------------------------------------------

## 0.6.0 (Development) --- Platform Architecture & Documentation

### Added

#### Documentation

-    Reorganized documentation into Architecture, SDK, Platform, Deployment, and Development sections.
-    Added Platform overview documentation.
-    Added Platform Services architecture documentation.
-    Added Deployment guide.
-    Added Testing guide.
-    Modernized project README.
-    Standardized subsystem documentation across Hardware, Drive, Sensors, Vision, Audio, and System.
-    Added placeholder operational documentation for future platform features.

#### Architecture

-    Standardized Robot Platform architecture.
-    Clarified the distinction between the Betabox Robotics SDK and the Betabox Robot Platform.
-    Standardized subsystem responsibilities and resource ownership.
-    Established long-term platform roadmap.

### Changed

-    Updated documentation to reflect the stable Robot API.
-    Updated deployment documentation to describe the complete platform rather than only the SDK.
-    Reorganized project documentation for future Launchpad development.

------------------------------------------------------------------------

## 0.5.0 (Development) --- Stable Robot Platform

### Added

#### Robot Platform

-    Stable Robot API.
-    Robot hierarchy (`RobotBase`, `Robot`, `CarRobot`, `BetaboxCar`).
-    Robot composition model.
-    Robot configuration model.
-    Convenience Robot API.
-    Context manager support.
-    Resource ownership model.
-    Betabox Car implementation.

#### Audio

-    Reusable Audio subsystem.
-    Pluggable speech backend architecture.
-    Pico, espeak-ng, and optional Piper speech backends.
-    Sound playback.
-    Tone generation.
-    Melody playback.
-    Pronunciation preprocessing.
-    Speaker amplifier management.
-    Audio validation tests and examples.

#### System

-    Reusable System subsystem.
-    Platform status and health foundation.
-    Media path management.
-    System validation tests and examples.

### Changed

-    Finalized reusable subsystem composition.
-    Standardized subsystem construction using default factories.
-    Unified the public Robot API across subsystems.

------------------------------------------------------------------------

## 0.4.0 (Development) --- Vision Platform

### Added

-    Modular Vision subsystem.
-    Camera abstraction.
-    Shared frame pipeline.
-    Snapshot service.
-    Recording service.
-    WebRTC streaming.
-    Metadata bus.
-    Overlay rendering.
-    Detection framework.
-    Color detection.
-    Face detection.
-    TensorFlow Lite runtime foundation.
-    Vision validation tests and developer examples.

### Changed

-    Replaced MJPEG-centric design with a transport-independent architecture.
-    Separated metadata from video transport.
-    Established a shared pipeline for streaming, recording, snapshots, and future AI inference.

------------------------------------------------------------------------

## 0.3.0 (Development) --- Reusable Robot Subsystems

### Added

#### Drive

-    Reusable Drive subsystem.
-    Steering support.
-    Validation tests and examples.

#### Sensors

-    Sensors subsystem.
-    Ultrasonic sensor.
-    Grayscale sensor.
-    Battery monitoring.
-    ADC abstraction.
-    Validation tests and examples.

------------------------------------------------------------------------

## 0.2.0 (Development) --- Hardware Foundation

### Added

-    Backend-independent Pin abstraction.
-    I²C abstraction.
-    PWM abstraction.
-    Motor abstraction.
-    Servo abstraction.
-    Hardware exception hierarchy.
-    Standardized pin namespace.
-    Initial project structure for tests and examples.

### Changed

-    Adopted composition over inheritance throughout the hardware layer.
-    Established the foundational Betabox hardware architecture.

------------------------------------------------------------------------

## 0.1.0 (Development) --- Project Initialization

### Added

-    Initial repository structure.
-    Python package foundation.
-    Development environment.
-    Initial documentation.
-    Versioning support.

------------------------------------------------------------------------

## Future Milestones

Planned future milestones include:

-    Configuration & Platform Services
-    Launchpad
-    Classroom Platform
-    Additional Betabox Robot Platforms
-    Version 1.0
