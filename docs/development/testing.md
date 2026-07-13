# Betabox Testing Guide

**Status:** Development Guide\
**Project:** Betabox Robot Platform\
**Document:** `testing.md`

------------------------------------------------------------------------

## Purpose

This document describes the recommended testing strategy for the Betabox Robot Platform.

Testing is organized into multiple layers so that individual hardware abstractions, reusable subsystems, robot implementations, and the complete platform can each be validated independently.

No feature is considered complete until it has been documented, implemented, and verified.

------------------------------------------------------------------------

## Testing Philosophy

Testing should be:

-    Repeatable
-    Hardware-aware
-    Easy to execute
-    Safe for classroom hardware
-    Focused on one layer at a time

The testing strategy mirrors the platform architecture.

``` text
    Unit Tests
        │
        ▼
Hardware Validation
        │
        ▼
Subsystem Validation
        │
        ▼
  Robot Validation
```

------------------------------------------------------------------------

## Test Organization

``` text
tests/
├── hardware/
├── drive/
├── sensors/
├── vision/
├── audio/
├── system/
└── robots/
```

Each directory validates a specific layer of the platform.

------------------------------------------------------------------------

## Hardware Validation

Hardware validation verifies reusable hardware abstractions on a physical robot.

Examples include:

-    GPIO
-    PWM
-    ADC
-    I²C
-    Servo
-    Motor

These tests verify that low-level hardware behaves correctly before it is composed into higher-level subsystems.

------------------------------------------------------------------------

## Subsystem Validation

Subsystem validation verifies complete reusable subsystems.

Current subsystem areas include:

-    Drive
-    Sensors
-    Vision
-    Audio
-    System

These tests use the configured robot hardware while validating reusable subsystem implementations.

------------------------------------------------------------------------

## Robot Validation

Robot validation verifies the public Robot API.

Typical areas include:

-    Lifecycle
-    Convenience APIs
-    Robot capabilities
-    Health reporting
-    End-to-end behavior

Robot validation confirms that students interact with a stable programming interface.

------------------------------------------------------------------------

## Vision Testing

Vision includes additional validation because it combines hardware, services, and computer vision.

Tests include:

-    Camera
-    Frame pipeline
-    Recording
-    Snapshots
-    Metadata
-    Overlay rendering
-    Detectors
-    WebRTC
-    Vision service integration

Some vision tests require the managed video service to be stopped before execution.

------------------------------------------------------------------------

## Running Tests

Activate the development environment:

``` bash
source /opt/betabox/venv/bin/activate
```

Run an individual test:

``` bash
python -m betabox_robotics.tests.hardware.test_pwm
```

Run a subsystem test:

``` bash
python -m betabox_robotics.tests.sensors.test_ultrasonic
```

Run a robot test:

``` bash
python -m betabox_robotics.tests.robots.test_robot_api
```

Run all tests:

``` bash
find tests -name "test_*.py" | sort | while read test; do
    module=${test%.py}
    module=${module//\//.}
    python -m betabox_robotics.$module || break
done
```

------------------------------------------------------------------------

## Expected Environment

Tests are intended to run on a configured Betabox robot.

Recommended environment:

-    Raspberry Pi OS Bookworm
-    Python 3.11
-    Robot HAT
-    Camera installed
-    Audio hardware available
-    Platform deployed using the supported installer

------------------------------------------------------------------------

## Writing New Tests

Every new public feature should include:

-    Documentation
-    Example program
-    Appropriate tests

Choose the correct validation level:

-    Hardware abstraction
-    Reusable subsystem
-    Robot API
-    Platform integration

Avoid duplicating tests across layers.

------------------------------------------------------------------------

## Best Practices

-    Test one responsibility at a time.
-    Keep tests deterministic.
-    Prefer reusable fixtures where practical.
-    Clean up hardware resources after each test.
-    Keep robot state predictable between tests.

------------------------------------------------------------------------

## Relationship to Validation

Testing verifies implementation correctness.

Validation confirms the platform behaves correctly on supported hardware.

See `validation.md` for the complete validation strategy.

------------------------------------------------------------------------

## Summary

The Betabox testing strategy validates the platform from the hardware layer through the public Robot API.

By separating hardware, subsystem, robot, and integration testing, the platform remains reliable while allowing internal implementations to evolve without breaking the student programming experience.
