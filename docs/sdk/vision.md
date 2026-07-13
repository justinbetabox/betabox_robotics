# Betabox Vision Subsystem

**Status:** Subsystem Design Specification\
**Project:** Betabox Robot Platform\
**Document:** `vision.md`

------------------------------------------------------------------------

## Purpose

The Vision subsystem provides a stable, reusable interface for camera
access, snapshots, recording, streaming, and computer vision.

It presents a simple, hardware-independent API while hiding the details
of camera drivers, streaming transports, frame pipelines, metadata
management, and operating-system-specific implementation.

Student code should describe **what visual capability it needs**, not
how cameras, transports, or frame processing are implemented.

------------------------------------------------------------------------

## Robot Composition

The Vision subsystem is a reusable subsystem implementation composed
into a robot implementation.

Robot implementations provide the configuration required to construct
the Vision subsystem, including camera settings, storage locations, and
platform-specific hardware.

Applications should normally access vision capabilities through the
Robot API:

``` python
from betabox_robotics import BetaboxCar

with BetaboxCar() as car:
    photo = car.capture()
```

The Vision subsystem remains available for more detailed control:

``` python
car.vision.capture()
car.vision.start()
car.vision.start_recording("demo.mp4")
```

Constructing low-level vision components directly is generally reserved
for hardware validation, subsystem validation, testing, and advanced
development.

------------------------------------------------------------------------

## Responsibilities

### Camera

-    Exclusive camera ownership
-    Camera lifecycle
-    Camera configuration

### Frame Pipeline

-    Frame acquisition
-    Frame distribution
-    Consumer management

### Vision Services

-    Snapshots
-    Recording
-    Streaming
-    Detection

### Metadata

-    Structured metadata publication
-    Detection results
-    Stream statistics

### Resource Management

-    Camera ownership
-    Consumer lifecycle
-    Failure recovery

------------------------------------------------------------------------

## Non-Responsibilities

The Vision subsystem is **not** responsible for:

-    Robot movement
-    Sensor acquisition
-    Audio playback
-    Platform management
-    Autonomous navigation
-    Path planning

Vision provides perception.

Higher-level software decides how the robot should respond to the
information produced by Vision.

------------------------------------------------------------------------

## Public API

### Robot API

``` python
car.start_vision()
car.stop_vision()

car.capture("photo.jpg")

car.start_recording("demo.mp4")
car.stop_recording()

car.is_vision_running()
car.is_recording()
```

### Vision Subsystem API

``` python
car.vision.start()
car.vision.stop()

car.vision.capture("photo.jpg")

car.vision.start_recording("demo.mp4")
car.vision.stop_recording()
```

------------------------------------------------------------------------

## Architectural Goals

-    Single camera ownership
-    Stable public Vision API
-    Transport-independent streaming
-    Shared frame pipeline
-    Metadata independent of rendered video
-    Multiple concurrent consumers
-    Safe resource management
-    Straightforward extensibility

------------------------------------------------------------------------

## Core Principles

-    The camera has exactly one owner.
-    Components communicate through stable interfaces.
-    Processing is independent of transport.
-    Streaming never owns the camera.
-    Consumers subscribe to frames.
-    Detection publishes metadata rather than modifying frames.
-    New capabilities integrate into the existing pipeline.

------------------------------------------------------------------------

## Internal Architecture

``` text
             Camera
                │
                ▼
          Frame Source
                │
     ┌──────────┼───────────┐
     ▼          ▼           ▼
 Streaming   Recording   Detection
     │          │           │
     └──────────┼───────────┘
                ▼
           Metadata Bus
                │
                ▼
        Overlay Renderer
```

A single frame pipeline distributes frames to any number of independent
consumers.

------------------------------------------------------------------------

## Metadata Bus

The Metadata Bus publishes structured information independently from
rendered video.

Examples include:

-    Detections
-    Bounding boxes
-    Labels
-    Confidence values
-    Tracking IDs
-    Stream statistics
-    Camera state

Metadata remains transport-independent and may be consumed by streaming,
recordings, browser overlays, or future services.

------------------------------------------------------------------------

## Overlay Rendering

Detectors publish metadata rather than drawing on frames.

Overlay rendering is optional and may be applied independently to:

-    Snapshots
-    Recordings
-    Streams

The original frame always remains unchanged.

------------------------------------------------------------------------

## Detection

Detection components consume frames and publish structured metadata.

Detectors:

-    Never own the camera
-    Never depend on streaming transports
-    Never permanently modify captured frames

Built-in detectors currently include:

-    Color detection
-    Face detection
-    Pluggable object detection

------------------------------------------------------------------------

## Resource Ownership

The Vision subsystem owns:

-    Camera
-    Frame pipeline
-    Frame consumers
-    Detector lifecycle
-    Metadata publication

Other subsystems should never access the camera directly.

------------------------------------------------------------------------

## Interaction with Other Subsystems

``` text
        Robot API
            │
            ▼
          Vision
            │
            ▼
       Metadata Bus
            │
            ▼
Drive / Portal / Applications
```

Vision publishes perception.

Other subsystems decide how to use it.

------------------------------------------------------------------------

## Implementation Details

The public API intentionally hides implementation details such as:

-    Camera libraries
-    WebRTC
-    HTTP signaling
-    VisionClient
-    Managed services
-    FFmpeg
-    OpenCV internals
-    Overlay implementation

These may evolve without changing the public API.

### Managed Implementation

Normal robot operation uses a managed vision service that owns the
physical camera and coordinates streaming, recording, snapshots, and
detection.

Applications interact through the Robot API rather than directly with
the managed service.

------------------------------------------------------------------------

## Future Expansion

Future capabilities may include:

-    QR codes
-    AprilTags
-    Pose estimation
-    OCR
-    Semantic segmentation
-    Multi-object tracking
-    Depth cameras
-    Stereo vision
-    AI acceleration
-    Additional streaming transports
-    Browser overlays

Future capabilities should integrate through existing interfaces
whenever practical.

------------------------------------------------------------------------

## Testing and Validation

The Vision subsystem should be verified through:

-    Unit tests
-    Hardware validation
-    Subsystem validation
-    Robot validation

Subsystem validation verifies the complete shared vision pipeline using
a configured robot implementation.

------------------------------------------------------------------------

## Design Principles

The Vision subsystem follows the Betabox Platform Design Principles:

-    Student First
-    Stable Public API
-    Reusable Subsystems
-    Hardware Independence
-    Exclusive Resource Ownership
-    Safe by Default
-    Test Everything

------------------------------------------------------------------------

## Summary

The Vision subsystem provides a modular, transport-independent
foundation for camera access, snapshots, recording, streaming, and
computer vision.

It owns the camera, distributes frames through a shared pipeline,
publishes structured metadata, and exposes a stable Robot API while
hiding implementation details.

New transports, detectors, overlays, and AI capabilities can be added
without changing the public programming model.
