# Betabox Robot API Reference

> **Audience:** Curriculum authors and application developers using
> `BetaboxCar`.

This document summarizes the primary public API exposed by `BetaboxCar`.
Advanced subsystem APIs are documented separately.

------------------------------------------------------------------------

## Movement

  Method                       Returns         Description
  ---------------------------- --------------- ---------------------------------
  `forward(speed: float)`      `None`          Drive forward.
  `backward(speed: float)`     `None`          Drive backward.
  `stop()`                     `None`          Stop the robot.
  `left(angle: float = 30)`    `None`          Turn steering left.
  `right(angle: float = 30)`   `None`          Turn steering right.
  `center()`                   `None`          Center steering.
  `drive_status()`             `DriveStatus`   Current drive subsystem status.

## Camera Mount

  Method                    Returns
  ------------------------- ---------------------
  `look(...)`               `None`
  `camera_pan(angle)`       `None`
  `camera_tilt(angle)`      `None`
  `look_center()`           `None`
  `camera_mount_status()`   `CameraMountStatus`

## Audio

  Method                        Returns
  ----------------------------- ---------------
  `say(text)`                   `None`
  `play(sound)`                 `None`
  `play_note(note, duration)`   `None`
  `play_melody(notes)`          `None`
  `stop_audio()`                `None`
  `is_audio_playing()`          `bool`
  `audio_status()`              `AudioStatus`

## Sensors

### Ultrasonic

  Method                   Returns
  ------------------------ ---------------------
  `distance(samples=10)`   `float`
  `distance_reading()`     `UltrasonicReading`

### Battery

  Method                    Returns
  ------------------------- ------------------
  `battery_voltage()`       `float`
  `battery_status()`        `BatteryState`
  `battery_reading()`       `BatteryReading`
  `is_battery_low()`        `bool`
  `is_battery_critical()`   `bool`

### Line Sensor

  Method                Returns
  --------------------- --------------------
  `line_values()`       `list[int]`
  `line_normalized()`   `list[float]`
  `line_status()`       `list[int]`
  `line_reading()`      `GrayscaleReading`

### Sensor Summary

  Method               Returns
  -------------------- -----------------
  `sensors_status()`   `SensorsStatus`

## Vision

  Method                       Returns
  ---------------------------- -----------------------------
  `snapshot()`                 `ClientSnapshot`
  `capture()`                  `ClientSnapshot`
  `start_recording()`          `Path`
  `stop_recording()`           `ClientRecording`
  `is_recording()`             `bool`
  `is_vision_running()`        `bool`
  `vision_stats()`             `ClientVisionStatistics`
  `metadata()`                 `ClientMetadata \| None`
  `enable_detection()`         `ClientDetectionStatus`
  `disable_detection()`        `ClientDetectionStatus`
  `detection_status()`         `ClientDetectionStatus`
  `enable_stream_overlay()`    `ClientStreamOverlayStatus`
  `disable_stream_overlay()`   `ClientStreamOverlayStatus`

## System

  Method                   Returns
  ------------------------ ----------------
  `hostname()`             `str`
  `ip_addresses()`         `list[str]`
  `media_paths()`          `MediaPaths`
  `ensure_media_paths()`   `MediaPaths`
  `status()`               `SystemStatus`
  `system_status()`        `SystemStatus`
  `system_health()`        `SystemHealth`

## Robot Health

  Method         Returns
  -------------- ---------------
  `health()`     `RobotHealth`
  `stop_all()`   `None`

------------------------------------------------------------------------

# Important Return Types

These methods return rich objects that should be documented separately
as dataclass references:

-   DriveStatus
-   CameraMountStatus
-   BatteryReading
-   BatteryState
-   GrayscaleReading
-   UltrasonicReading
-   SensorsStatus
-   AudioStatus
-   SystemStatus
-   SystemHealth
-   RobotHealth
-   ClientSnapshot
-   ClientRecording
-   ClientMetadata
-   ClientDetectionStatus
-   ClientVisionStatistics
-   ClientStreamOverlayStatus

## Recommended Follow-up

Create one reference page for each return type documenting:

-   Fields
-   Field types
-   Meaning
-   Example values
-   Typical usage

This document serves as the high-level API index for the public Betabox
robot interface.
