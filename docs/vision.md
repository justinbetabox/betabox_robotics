# Betabox Vision Platform Architecture

**Status:** Stable Architecture Specification\
**Project:** Betabox Robot Platform\
**Phase:** Vision Platform

------------------------------------------------------------------------

## Purpose

This document defines the long-term architecture of the Betabox Vision Platform.

It intentionally describes the architectural contracts of the Vision
subsystem rather than specific implementation details. Internal
implementations may evolve, but the architecture, responsibilities, and
public interfaces described here should remain stable.

The Vision Platform is designed to provide a modular,
transport-independent foundation for camera access, streaming, computer
vision, recording, snapshots, and future AI capabilities.

------------------------------------------------------------------------

## Robot Composition

The Vision subsystem is a reusable subsystem implementation.

Robot implementations provide any platform-specific configuration
required to initialize the Vision subsystem.

Applications should normally access vision capabilities through:

```python
from betabox_car import Robot

robot = Robot()

robot.vision.snapshot.capture()
```

The Vision subsystem should not depend on robot-specific configuration
internally.

------------------------------------------------------------------------

## Responsibilities

The Vision subsystem is responsible for:

### Camera

-    Camera ownership
-    Camera lifecycle
-    Camera configuration

### Frame Pipeline

-    Frame acquisition
-    Frame distribution
-    Consumer management

### Vision Services

-    Streaming
-    Snapshots
-    Recording
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

The Vision subsystem provides perception.

Higher-level systems determine how the robot should respond to the
information produced by Vision.

------------------------------------------------------------------------

## Architectural Goals

-    Single camera ownership
-    Stable public Vision API
-    Transport-independent streaming
-    Transport-independent detection
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
-    Consumers subscribe to frames rather than requesting them directly.
-    Detection publishes metadata rather than modifying frames.
-    New capabilities should integrate by subscribing to the existing pipeline instead of introducing parallel pipelines.

------------------------------------------------------------------------

## Architectural Overview

``` text
                   Vision
                      │
                      ▼
                   Camera
                      │
                      ▼
                 Frame Source
                      │
                      ▼
                 Frame Consumers
                      │
  ┌──------┬──--------┼─────────---─---──┐
  │        │          │                  │
  ▼        ▼          ▼                  ▼
WebRTC Recording   Snapshot      Detection Manager
                                         │
                                         ▼
                                     Detectors
                                         │
                                         ▼
                                    Metadata Bus
```

The Vision subsystem is organized around a single frame pipeline.

SnapshotService retrieves the latest available frame through the FrameProvider protocol. This allows still images to be captured without subscribing as a frame consumer or depending on a concrete FrameSource implementation. Unlike streaming and recording, SnapshotService does not subscribe as a continuous frame consumer.

The camera produces frames exactly once. Those frames are distributed to
any number of independent consumers. Consumers should not communicate
directly with one another unless required by a separate interface.

The architecture has been validated with simultaneous WebRTC streaming, recording, snapshots, and detection operating from a single camera instance without requiring additional camera ownership.

------------------------------------------------------------------------

## Camera

The Camera component is responsible for:

-    Exclusive ownership of camera hardware
-    Camera configuration
-    Lifecycle management
-    Frame acquisition
-    Safe startup and shutdown
-    Recovery from failures

Higher layers should never depend directly on the underlying camera
library.

------------------------------------------------------------------------

## Frame Source

The Frame Source exposes the latest available frame through the FrameProvider protocol. Components that only require access to the most recent frame should depend on this protocol rather than the concrete FrameSource implementation.

Responsibilities include:

-    Consumer registration
-    Consumer removal
-    Frame distribution
-    Thread-safe operation
-    Multiple simultaneous consumers

The Frame Source is intentionally unaware of what consumers do with the
frames they receive.

------------------------------------------------------------------------

## Frame Consumers

Frame consumers perform work using frames supplied by the Frame Source.

Typical consumers include:

-    Live streaming
-    Snapshot generation
-    Recording
-    Detection
-    Future AI inference

Consumers should remain independent so that they can be enabled,
disabled, replaced, or tested individually.

------------------------------------------------------------------------

## Metadata Bus

The Metadata Bus provides structured information that accompanies video
without becoming part of the video itself.

Examples include:

-    detections
-    bounding boxes
-    labels
-    confidence values
-    tracking IDs
-    timestamps
-    stream statistics
-    camera state

Separating metadata from video allows different clients to present
information differently while preserving the original image.

The Metadata Bus is transport-independent and may be consumed simultaneously by streaming transports, browser overlays, recordings, local applications, and future platform services.

------------------------------------------------------------------------

## Detection Pipeline

``` text
     Frame
       │
       ▼
Detection Manager
       │
       ▼
   Detectors
       │
       ▼
  Metadata Bus
```

The Detection Manager owns the built-in detector implementations and coordinates execution of all registered detectors. Built-in detectors are exposed as capabilities of the Vision subsystem, while additional detectors may be registered programmatically to extend the platform.

Detectors consume frames and publish structured metadata through the Metadata Bus. They should not own the camera, depend on the streaming transport, or permanently modify captured frames.

------------------------------------------------------------------------

## Streaming

Streaming is treated as a transport implementation rather than part of
the camera pipeline.

All streaming implementations should present a consistent conceptual
interface:

``` text
start()
stop()
clients()
statistics()
```

The initial transport is WebRTC.

Future transports may include:

-   RTSP
-   Local preview
-   File output
-   SRT

Changing transports should not require architectural changes elsewhere
in the Vision subsystem.

------------------------------------------------------------------------

## Recording

The Recording Service captures video from the shared Vision frame
pipeline.

Recording does not own or open the camera. Instead, it subscribes to the
Frame Source as a `FrameConsumer`, allowing recording to operate
simultaneously with streaming, snapshots, and future detectors.

Capabilities:

-    MP4 recording
-    Timestamped filenames
-    Per-user storage (`~/media/videos`)
-    Shared camera pipeline
-    Concurrent operation with other consumers

------------------------------------------------------------------------

## Snapshots

The Snapshot Service captures still images from the existing Vision frame
pipeline.

Snapshots do not open or own the camera. Instead, the service retrieves
the latest available frame from the shared `FrameProvider` interface,
allowing snapshots to coexist with streaming, recording, and future
detectors.

Capabilities:

-    JPEG and PNG output
-    Timestamped filenames
-    Per-user storage (`~/media/pictures`)
-    Shared camera pipeline
-    Timestamp metadata

------------------------------------------------------------------------

## Resource Management

The Vision subsystem owns:

-    Camera
-    Frame pipeline
-    Frame consumers
-    Detector lifecycle
-    Metadata publication

Other subsystems should never access the camera directly.

These guarantees are particularly important for classroom environments
where multiple applications may interact with Vision.

------------------------------------------------------------------------

## Interaction with Other Subsystems

Applications interact with Vision through the Robot API.

Vision provides perception capabilities to higher-level software by
publishing frames and structured metadata.

Vision does not command other subsystems directly.

Example:

     Applications
          │
          ▼
      Robot API
          │
          ▼
        Vision
          │
          ▼
     Metadata Bus
           │
           ▼
Navigation / Drive / Portal

------------------------------------------------------------------------

## Public Vision API

The public Vision API is organized around capabilities rather than implementations. Details of the public programming interface are defined in api.md. The architecture described in this document is intended to support a stable API even as internal implementations evolve.

------------------------------------------------------------------------

## Future Expansion

The architecture is intended to support future capabilities without
redesign.

Future capabilities should integrate by implementing existing interfaces whenever possible rather than introducing new architectural patterns.

Examples include:

-    QR codes
-    AprilTags
-    Pose estimation
-    OCR
-    Semantic segmentation
-    Multi-object tracking
-    Depth cameras
-    Stereo vision
-    AI acceleration
-    Browser overlays
-    Additional streaming transports
-    Additional detector plugins

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

The Vision subsystem provides a modular, transport-independent foundation
for camera access, streaming, recording, snapshots, and computer vision.

It owns the camera, distributes frames through a shared pipeline, and
publishes structured metadata while remaining independent of transport
implementations and robot-specific configuration.

This architecture allows new capabilities to be added through
composition rather than architectural redesign while preserving a stable
public Vision API.
