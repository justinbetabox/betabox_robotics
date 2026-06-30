# Betabox Vision Platform Design

**Status:** Draft Architecture (Pre-Implementation)\
**Project:** Betabox Robot Platform\
**Phase:** Vision Platform

------------------------------------------------------------------------

# Purpose

This document defines the long-term architecture of the Betabox Vision
Platform. It is intended to be the stable design specification before
implementation begins.

The goal is to create a vision subsystem that is transport-independent,
modular, and scalable while providing low-latency video streaming,
computer vision, recording, snapshots, and future AI capabilities.

------------------------------------------------------------------------

# Goals

-   Single owner of the camera hardware
-   Stable public Vision API
-   Streaming independent from processing
-   Detection independent from streaming
-   Modular pipeline
-   Hardware-accelerated video when available
-   Easy future expansion

------------------------------------------------------------------------

# Current Architecture

``` text
Pi Camera
    │
OpenCV / Vilib
    │
JPEG Encoding
    │
Flask MJPEG
    │
Browser
```

## Current Issues

-   MJPEG consumes significant bandwidth.
-   JPEG encoding is CPU intensive.
-   High latency.
-   No adaptive bitrate.
-   Camera ownership is difficult to manage.
-   Streaming and processing are tightly coupled.

------------------------------------------------------------------------

# Design Principles

1.  One camera owner.
2.  Everything communicates through stable interfaces.
3.  Processing never depends on transport.
4.  Streaming never owns the camera.
5.  Detection publishes metadata instead of drawing directly.
6.  Future detectors should plug into the pipeline.

------------------------------------------------------------------------

# High-Level Architecture

``` text
Vision
   │
┌─────────────────┴─────────────────┐
│                                   │
FrameSource                         MetadataBus
│
CameraManager
│
Picamera2
│
▼
FrameConsumers
│
┌────────┼──────────────┬──────────────┐
│        │              │              │
│        Streamer       Recorder       Detector
│        │                             │
│        WebRTC                        Metadata
│                                      │
└──────────────────────────────────────┘
```

------------------------------------------------------------------------

# Camera Manager

Responsibilities:

-   Own Picamera2
-   Configure camera
-   Start/stop capture
-   Deliver frames
-   Manage camera settings
-   Prevent multiple consumers from opening the camera

Public responsibilities:

-   start()
-   stop()
-   configure()
-   latest_frame()

------------------------------------------------------------------------

# Frame Pipeline

``` text
Camera
   │
FrameSource
   │
Raw Frame
   │
Consumers
```

Consumers include:

-   Streamer
-   Recorder
-   Snapshot
-   Detection

No consumer opens the camera directly.

------------------------------------------------------------------------

# Detection Pipeline

``` text
Frame
   │
Detectors
   ├── Color
   ├── Face
   ├── Objects
   ├── Traffic Signs
   └── Future AI Models
   │
Metadata
```

Metadata examples:

-   bounding boxes
-   confidence
-   labels
-   tracking IDs
-   timestamps

The detector should not render overlays.

------------------------------------------------------------------------

# Streaming Layer

The platform defines a generic streaming interface.

``` text
Streamer Interface

start()
stop()
clients()
statistics()
```

The first implementation will be WebRTC.

Future implementations may include:

-   RTSP
-   Local preview
-   File output
-   SRT

The rest of the platform should not require modification to support
alternate transports.

------------------------------------------------------------------------

# Why WebRTC

Benefits:

-   Lower latency
-   Adaptive bitrate
-   Congestion control
-   Browser native
-   Hardware H.264 support
-   Better scalability than MJPEG

WebRTC replaces only the transport layer.

------------------------------------------------------------------------

# Recording

Recording subscribes to the frame pipeline.

Capabilities:

-   MP4 recording
-   Timestamped filenames
-   User directories
-   Future scheduled recording

------------------------------------------------------------------------

# Snapshots

Snapshot service receives the latest frame from the Camera Manager.

Capabilities:

-   PNG/JPEG
-   User storage
-   Timestamp metadata

------------------------------------------------------------------------

# Resource Management

The Camera Manager is responsible for:

-   Exclusive camera ownership
-   Consumer registration
-   Safe startup/shutdown
-   Failure recovery
-   Camera state monitoring

------------------------------------------------------------------------

# Public Vision API

Example capability groups:

-   Camera
-   Stream
-   Detection
-   Recording
-   Snapshots
-   Configuration
-   Statistics

The API should remain stable even if internal implementations change.

------------------------------------------------------------------------

# Future Extensions

Potential additions:

-   QR code detection
-   AprilTags
-   Pose estimation
-   OCR
-   Semantic segmentation
-   Multi-object tracking
-   Depth cameras
-   Stereo vision
-   AI inference acceleration

------------------------------------------------------------------------

# Initial Implementation Plan

1.  Create Camera Manager.
2.  Create Frame Source.
3.  Create Streamer interface.
4.  Implement WebRTC streamer.
5.  Move existing detectors to the new pipeline.
6.  Move recording.
7.  Move snapshots.
8.  Add resource management.
9.  Remove Flask MJPEG.
10. Optimize performance.

------------------------------------------------------------------------

# Success Criteria

The finished Vision Platform should provide:

-   One camera owner
-   Multiple simultaneous consumers
-   Stable Vision API
-   Transport-independent architecture
-   Low-latency streaming
-   Easy extensibility
-   Reliable classroom operation

This document serves as the architectural foundation for all future
Betabox Vision development.
