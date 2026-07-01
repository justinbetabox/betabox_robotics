# CHANGELOG

## 0.5.0 (Development) — Platform Services

### Added

#### System

##### Foundation

- System subsystem foundation.
- System status model.
- Media path management.
- System validation test.
- System developer example.

------------------------------------------------------------------------

## 0.4.0 (Development) — Vision Platform

### Added

#### Vision

##### Foundation

- Modular Vision subsystem.
- Camera abstraction.
- Frame abstraction.
- Frame source pipeline.
- Frame consumer architecture.
- Metadata model.
- Metadata bus.
- FrameProvider protocol for Vision services.
- Vision test framework.

##### Streaming

- Transport-independent streaming architecture.
- Generic streaming abstraction.
- WebRTC streaming implementation.
- WebRTC signaling.
- WebRTC developer example.

##### Snapshots

- Vision snapshot service.
- Snapshot data model.
- Snapshot validation test.
- Snapshot developer example.

##### Recording

- Vision recording service.
- Recording data model.
- Thread-safe recording pipeline.
- MP4 recording support.
- Recording validation test.
- Recording developer example.
- Validated concurrent WebRTC streaming and recording from a shared frame pipeline.
- Per-user media storage for snapshots and recordings.

##### Detection

- Detector abstraction.
- Detection manager.
- Built-in detector architecture.
- Color detection.
- Multi-color detection.
- Face detection.
- Object detection architecture foundation.
- Object detection runtime abstraction.
- TensorFlow Lite runtime foundation.
- Detection validation tests.
- Detection developer examples.

#### Documentation

- Vision architecture specification.
- Public Robot API specification.
- Platform architecture documentation.
- Design principles.
- Roadmap updates.

### Changed

- Transitioned Vision from MJPEG-based streaming toward a transport-independent WebRTC architecture.
- Adopted a modular frame pipeline for streaming, recording, snapshots, and future AI inference.
- Separated metadata from video transport.
- Adopted a capability-oriented detection API for built-in Vision detectors.

------------------------------------------------------------------------

## 0.3.0 (Development) — Drive & Sensors

### Added

#### Drive

##### Foundation

- Drive subsystem.
- Default drive hardware factory.
- Drive validation tests.
- Drive developer examples.

#### Sensors

##### Foundation

- Sensors subsystem wrapper.
- Ultrasonic sensor abstraction.
- Grayscale sensor abstraction.
- Battery subsystem.

##### Hardware

- ADC hardware abstraction.
- Analog channel support through `Pins.A0` to `Pins.A7`.

##### Validation

- Ultrasonic validation tests.
- Grayscale validation tests.
- Battery validation tests.
- ADC validation tests.
- Ultrasonic developer examples.
- Grayscale developer examples.
- Battery developer examples.

------------------------------------------------------------------------

## 0.2.0 (Development) — Hardware Foundation

### Added

#### Hardware

##### Foundation

- Backend-independent Pin abstraction.
- Backend-independent I²C abstraction.
- Backend-independent PWM abstraction.
- Motor abstraction.
- Servo abstraction using composition.
- Hardware exceptions.
- Pins namespace (`Pins.D0`, `Pins.P0`, etc.).

##### Project

- Versioning support.
- Project documentation structure.
- Tests and examples directory structure.

### Changed

- Replaced inheritance with composition throughout the hardware layer.
- Introduced explicit hardware state management.
- Established the foundational Betabox API philosophy.

------------------------------------------------------------------------

## 0.1.0 (Development) — Project Initialization

### Added

- Initial project structure.
- Repository layout.
- Development environment.
- Initial documentation.
