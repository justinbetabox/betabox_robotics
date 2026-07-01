# Betabox Vision Platform Architecture

**Status:** Stable Architecture Specification\
**Project:** Betabox Robot Platform\
**Phase:** Vision Platform

------------------------------------------------------------------------

# Purpose

This document defines the long-term architecture of the Betabox Vision Platform.

It intentionally describes the architectural contracts of the Vision
subsystem rather than specific implementation details. Internal
implementations may evolve, but the architecture, responsibilities, and
public interfaces described here should remain stable.

The Vision Platform is designed to provide a modular,
transport-independent foundation for camera access, streaming, computer
vision, recording, snapshots, and future AI capabilities.

------------------------------------------------------------------------

# Architectural Goals

-   Single owner of camera hardware
-   Stable public Vision API
-   Transport-independent streaming
-   Detection independent from transport
-   Modular frame pipeline
-   Metadata independent from rendered video
-   Support multiple simultaneous consumers
-   Safe resource management
-   Straightforward future expansion

------------------------------------------------------------------------

# Core Principles

1.  The camera has exactly one owner.
2.  Components communicate through stable interfaces.
3.  Processing is independent of transport.
4.  Streaming never owns the camera.
5.  Consumers subscribe to frames rather than requesting them directly.
6.  Detection publishes metadata rather than modifying frames.
7.  New capabilities should integrate by subscribing to the existing
    pipeline instead of introducing parallel pipelines.

------------------------------------------------------------------------

# Architectural Overview

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
┌────┼──────────┬─────────────┬──────────────────┐
│    │          │             │
▼    ▼          ▼             ▼
WebRTC Recording Snapshot Detection Manager
                                  │
                                  ▼
                              Detectors
                                  │
                                  ▼
                             Metadata Bus
```

The Vision subsystem is organized around a single frame pipeline.

SnapshotService retrieves the latest available frame through the FrameProvider protocol. This allows still images to be captured without subscribing as a frame consumer or depending on a concrete FrameSource implementation.

The camera produces frames exactly once. Those frames are distributed to
any number of independent consumers. Consumers should not communicate
directly with one another unless required by a separate interface.

The architecture has been validated with simultaneous WebRTC streaming, recording, snapshots, and detection operating from a single camera instance without requiring additional camera ownership.

------------------------------------------------------------------------

# Camera Layer

Responsibilities include:

-   Exclusive ownership of camera hardware
-   Camera configuration
-   Lifecycle management
-   Frame acquisition
-   Safe startup and shutdown
-   Recovery from failures

Higher layers should never depend directly on the underlying camera
library.

------------------------------------------------------------------------

# Frame Source

The Frame Source exposes the latest available frame through the FrameProvider protocol. Components that only require access to the most recent frame should depend on this protocol rather than the concrete FrameSource implementation.

Responsibilities include:

-   Consumer registration
-   Consumer removal
-   Frame distribution
-   Thread-safe operation
-   Multiple simultaneous consumers

The Frame Source is intentionally unaware of what consumers do with the
frames they receive.

------------------------------------------------------------------------

# Frame Consumers

Frame consumers perform work using frames supplied by the Frame Source.

Typical consumers include:

-   Live streaming
-   Computer vision
-   Recording
-   Snapshot generation
-   Live Streaming
-   Detection
-   Recording
-   Future AI inference

Consumers should remain independent so that they can be enabled,
disabled, replaced, or tested individually.

------------------------------------------------------------------------

# Metadata Bus

The Metadata Bus provides structured information that accompanies video
without becoming part of the video itself.

Examples include:

-   detections
-   bounding boxes
-   labels
-   confidence values
-   tracking IDs
-   timestamps
-   stream statistics
-   camera state

Separating metadata from video allows different clients to present
information differently while preserving the original image.

------------------------------------------------------------------------

# Detection Pipeline

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

Detectors consume frames and publish metadata.

The Detection Manager owns the built-in detector implementations and coordinates execution of all registered detectors. Built-in detectors are exposed as capabilities of the Vision subsystem, while additional detectors may be registered programmatically to extend the platform.

Detectors consume frames and publish structured metadata. They should not own the camera, depend on the streaming transport, or permanently modify captured frames.


------------------------------------------------------------------------

# Streaming

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

# Recording

The Recording Service captures video from the shared Vision frame
pipeline.

Recording does not own or open the camera. Instead, it subscribes to the
Frame Source as a `FrameConsumer`, allowing recording to operate
simultaneously with streaming, snapshots, and future detectors.

Capabilities:

- MP4 recording
- Timestamped filenames
- Per-user storage (`~/media/videos`)
- Shared camera pipeline
- Concurrent operation with other consumers

------------------------------------------------------------------------

# Snapshots

The Snapshot Service captures still images from the existing Vision frame
pipeline.

Snapshots do not open or own the camera. Instead, the service retrieves
the latest available frame from the shared `FrameProvider` interface,
allowing snapshots to coexist with streaming, recording, and future
detectors.

Capabilities:

- JPEG and PNG output
- Timestamped filenames
- Per-user storage (`~/media/pictures`)
- Shared camera pipeline
- Timestamp metadata

------------------------------------------------------------------------

# Resource Management

The Vision subsystem is responsible for:

-   exclusive camera ownership
-   consumer lifecycle
-   safe shutdown
-   failure recovery
-   camera state monitoring
-   prevention of resource conflicts

These guarantees are particularly important for classroom environments
where multiple applications may interact with Vision.

------------------------------------------------------------------------

# Public Vision API

The public Vision API is organized around capabilities rather than implementations. Details of the public programming interface are defined in api.md. The architecture described in this document is intended to support a stable API even as internal implementations evolve.

------------------------------------------------------------------------

# Future Expansion

The architecture is intended to support future capabilities without
redesign.

Future capabilities should integrate by implementing existing interfaces whenever possible rather than introducing new architectural patterns.

Examples include:

-   QR codes
-   AprilTags
-   Pose estimation
-   OCR
-   Semantic segmentation
-   Multi-object tracking
-   Depth cameras
-   Stereo vision
-   AI acceleration
-   Browser overlays
-   Additional streaming transports

------------------------------------------------------------------------

# Success Criteria

A successful Vision Platform provides:

-   one camera owner
-   multiple concurrent consumers
-   transport-independent architecture
-   stable public API
-   low-latency streaming
-   independent metadata
-   straightforward extensibility
-   reliable classroom operation

This document is the architectural reference for future Betabox Vision
development.
