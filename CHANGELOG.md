# CHANGELOG

## 0.4.0 (Development) --- Vision Platform

### Added

#### Vision

-   Modular Vision subsystem.
-   Camera abstraction.
-   Frame abstraction.
-   Frame source pipeline.
-   Frame consumer architecture.
-   Metadata model.
-   Metadata bus.
-   Generic streaming abstraction.
-   WebRTC streaming implementation.
-   WebRTC signaling.
-   Vision test suite.
-   WebRTC example application.
-   Vision snapshot service.
-   Snapshot data model.
-   Snapshot validation test.
-   Snapshot developer example.
-   FrameProvider protocol for Vision services.
-   Vision recording service.
-   Recording data model.
-   Thread-safe recording service.
-   MP4 recording support.
-   Recording validation test.
-   Recording developer example.
-   Validated concurrent WebRTC streaming and recording from a shared frame pipeline.
- Per-user media storage for snapshots and recordings.

#### Documentation

-   Vision architecture specification.
-   Public Robot API specification.
-   Platform architecture specification.
-   Platform design principles.
-   Roadmap updates.

### Changed

-   Transitioned Vision from MJPEG-based streaming toward a
    transport-independent WebRTC architecture.
-   Adopted a modular frame pipeline for future recording, snapshots,
    and AI inference.
-   Separated metadata from video transport.

------------------------------------------------------------------------

## 0.3.0 (Development) --- Drive & Sensors

### Added

#### Drive

-   Drive subsystem.
-   Default drive hardware factory.
-   Drive tests.
-   Drive examples.

#### Sensors

-   Sensors subsystem wrapper.
-   Ultrasonic sensor abstraction.
-   Grayscale sensor abstraction.
-   Grayscale calibration support.
-   ADC hardware abstraction.
-   Analog channel support through `Pins.A0` to `Pins.A7`.
-   ADC tests and examples.
-   Ultrasonic tests and examples.
-   Grayscale tests and examples.

------------------------------------------------------------------------

## 0.2.0 (Development) --- Hardware Foundation

### Added

-   New Betabox hardware architecture.
-   Backend-independent Pin abstraction.
-   Backend-independent I²C abstraction.
-   Backend-independent PWM abstraction.
-   Servo abstraction using composition.
-   Motor abstraction.
-   Pins namespace (`Pins.D0`, `Pins.P0`, etc.).
-   Hardware exceptions.
-   Versioning support.
-   Project documentation structure.
-   Tests and examples directory structure.

### Changed

-   Replaced inheritance with composition throughout the hardware layer.
-   Introduced explicit hardware state management.
-   Established the foundational Betabox API philosophy.

------------------------------------------------------------------------

## 0.1.0 (Development) --- Project Initialization

### Added

-   Initial project structure.
-   Repository layout.
-   Development environment.
-   Initial documentation.
