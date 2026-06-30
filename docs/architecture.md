# Betabox Car Architecture

## Philosophy

The Betabox Car SDK is designed around a stable public API independent
of the underlying hardware implementation.

Applications, curriculum, notebooks, and future web interfaces interact exclusively with the Betabox Robot API. They should never depend on hardware-specific libraries or Linux interfaces.

## Architecture

``` text
Student Code
        │
        ▼
   Betabox Car API
        │
        ▼
Subsystems
    Drive
    Sensors
    Vision
    Audio
    System
        │
        ▼
Platform Services
    Resource Manager
    Configuration
    Event System
        │
        ▼
Hardware Components
    Motor
    Servo
    PWM
    Pin
    I2C
        │
        ▼
Linux / Hardware Drivers
```

Each layer only communicates with the layer immediately below it.

## Design Goals

-   Stable public API
-   Backend-independent implementation
-   Composition over inheritance
-   One responsibility per class
-   Student-friendly programming interface
-   Physical concepts over hardware registers
-   Explicit behavior over implicit behavior
-   Exclusive ownership of shared hardware resources

## Hardware Components

The hardware layer provides low-level interfaces for physical devices
including GPIO, PWM, I2C, ADC, motors, servos, sensors, and future
hardware peripherals.

Higher layers should never communicate with Linux hardware interfaces
directly.

## Long-Term Goal

The Betabox Robot API is intended to become the stable programming interface for all Betabox robotic platforms. Applications, curriculum, notebooks, and future web interfaces should continue to function even as hardware implementations evolve. The platform should support replacing hardware, communication protocols, or internal implementations without requiring changes to user-facing code.
