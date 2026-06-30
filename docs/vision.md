# Betabox Vision Platform Architecture

**Status:** Stable Architecture Specification\
**Project:** Betabox Robot Platform\
**Phase:** Vision Platform

------------------------------------------------------------------------

# Purpose

This document defines the long-term architecture of the Betabox Vision
Platform.

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
      ┌─────────────┴─────────────┐
      │                           │
   Camera                    Metadata Bus
      │
      ▼
  Frame Source
      │
      ▼
 Frame Consumers
      │
 ┌────┼─────────┬─────────┬─────────┐
 │    │         │         │
WebRTC Detection Recording Snapshot
```

The Vision subsystem is organized around a single frame pipeline.

The camera produces frames exactly once. Those frames are distributed to
any number of independent consumers. Consumers should not communicate
directly with one another unless required by a separate interface.

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

The Frame Source distributes frames to registered consumers.

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
Detectors
   │
   ▼
Metadata Bus
```

Detectors consume frames and publish metadata.

They should not own the camera, depend on the streaming transport, or
permanently modify captured frames.

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

Recording subscribes to the frame pipeline.

Recording should never require opening a second camera instance.

------------------------------------------------------------------------

# Snapshots

Snapshots are generated from the existing frame pipeline.

Capturing a snapshot should not interrupt streaming, recording, or
detection.

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

The public API is organized around capabilities rather than
implementations.

Capability groups include:

-   Camera
-   Stream
-   Detection
-   Recording
-   Snapshots
-   Configuration
-   Statistics
-   Metadata

The public API should remain stable even when internal implementations
change.

------------------------------------------------------------------------

# Future Expansion

The architecture is intended to support future capabilities without
redesign.

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
