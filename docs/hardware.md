# Betabox Hardware Architecture

**Status:** Hardware Architecture Specification\
**Project:** Betabox Robot Platform\
**Document:** `hardware.md`

------------------------------------------------------------------------

# Purpose

The Hardware Layer provides a stable interface between the Betabox
platform and the physical robot hardware.

Its purpose is to isolate the rest of the platform from
hardware-specific implementation details. Higher-level components should
never communicate directly with GPIO, I²C, PWM controllers, Linux device
drivers, or board-specific hardware.

The Hardware Layer exposes physical concepts rather than hardware
implementation details.

------------------------------------------------------------------------

# Architecture

``` text
Applications
      │
      ▼
Subsystems
      │
      ▼
Physical Components
      │
      ▼
Hardware Devices
      │
      ▼
Hardware Interfaces
      │
      ▼
Linux / Physical Hardware
```

Each layer communicates only with the layer immediately below it.

------------------------------------------------------------------------

# Responsibilities

The Hardware Layer is responsible for:

-   Abstracting physical hardware
-   Hiding operating system interfaces
-   Managing hardware resources
-   Converting hardware values into physical units
-   Applying hardware calibration
-   Providing safe default behavior
-   Exposing stable hardware APIs

------------------------------------------------------------------------

# Non-Responsibilities

The Hardware Layer is **not** responsible for:

-   Vehicle behavior
-   Autonomous navigation
-   Obstacle avoidance
-   Line following
-   Vision processing
-   Camera streaming
-   Audio playback
-   User interfaces
-   Curriculum logic

Those responsibilities belong to higher-level subsystems.

------------------------------------------------------------------------

# Hardware Layers

The hardware package is organized into three logical layers.

## Layer 1 --- Hardware Interfaces

These classes communicate directly with Linux or the underlying hardware
platform.

Examples:

-   Pin
-   I2C
-   SPI (future)
-   UART (future)

Responsibilities:

-   GPIO access
-   Bus communication
-   Resource cleanup
-   Driver interaction
-   Error handling

These classes know nothing about motors, servos, sensors, or robot
behavior.

------------------------------------------------------------------------

## Layer 2 --- Hardware Devices

These classes understand specific hardware controllers.

Examples:

-   PWM
-   ADC

Responsibilities:

-   Register access
-   Timer configuration
-   Controller-specific behavior
-   Low-level device management

These classes hide controller implementation details from the rest of
the platform.

------------------------------------------------------------------------

## Layer 3 --- Physical Components

These classes represent actual robot hardware.

Examples:

-   Servo
-   Motor
-   Ultrasonic
-   Grayscale
-   Battery
-   Encoder (future)
-   IMU (future)

Responsibilities:

-   Physical units
-   Calibration
-   Safety limits
-   Device-specific behavior

Public APIs should expose concepts such as:

-   Degrees
-   Percent speed
-   Centimeters
-   Volts

rather than pulse widths, registers, or timing calculations.

------------------------------------------------------------------------

# Hardware Independence

Higher layers should never assume a particular hardware implementation.

Today:

``` text
Drive
    │
 Motor
    │
 PWM (Robot HAT)
```

Tomorrow:

``` text
Drive
    │
 Motor
    │
 PWM (RP2040)
```

The Drive subsystem should not require modification simply because the
underlying hardware implementation changes.

This principle allows the Betabox platform to support multiple hardware
platforms while maintaining a stable public API.

------------------------------------------------------------------------

# Hardware API

## Pin

Purpose: Digital GPIO access.

``` python
pin = Pin(Pins.D0)

pin.on()
pin.off()
pin.read()
pin.write(True)
```

## I2C

Purpose: Communicate with I²C devices.

``` python
bus = I2C(address=0x14)

bus.write(...)
bus.read(...)
bus.mem_read(...)
```

## PWM

Purpose: Generate PWM outputs using the underlying hardware controller.

``` python
pwm = PWM(Pins.P0)

pwm.set_frequency(50)
pwm.set_duty_cycle(50)
```

## ADC

Purpose: Read analog sensor values.

``` python
adc = ADC(Pins.A0)

value = adc.read()
voltage = adc.read_voltage()
```

The ADC class handles channel selection, register mapping, raw readings,
and voltage conversion.

## Servo

Purpose: Control standard RC servos using degrees.

``` python
servo = Servo(Pins.P0)

servo.center()
servo.move_to(30)
servo.move_to(-30)
```

Internally the Servo class manages calibration, angle limits, smooth
movement, pulse conversion, and PWM configuration.

## Motor

Purpose: Control a single DC motor.

``` python
motor.forward(50)
motor.backward(50)
motor.stop()
```

Internally the Motor class manages speed, direction, safe ramping, and
PWM output.

Motor calibration belongs to the Drive subsystem rather than the Motor
class.

## Ultrasonic

Purpose: Measure distance.

``` python
distance = ultrasonic.distance()
```

The Ultrasonic class manages trigger generation, echo timing, timeout
handling, and distance conversion.

## Grayscale

Purpose: Read the three-channel line sensor.

``` python
values = grayscale.read()
status = grayscale.status(values)
```

The Grayscale class manages ADC channels, calibration, thresholds,
normalization, and line detection.

------------------------------------------------------------------------

# Safe Defaults

The Hardware Layer should favor predictable, safe behavior.

Examples:

-   Servos move smoothly.
-   Motors ramp speed changes.
-   Resources are released cleanly.
-   Invalid parameters raise exceptions.
-   Hardware limits are enforced automatically.

Applications may opt into lower-level behavior when appropriate, but the
default API should protect both the hardware and the user.

------------------------------------------------------------------------

# Resource Ownership

Ownership always flows downward.

Example:

``` text
Drive
    │
Motor
    │
PWM
    │
I2C
```

Likewise:

``` text
Vision
    │
Camera
```

Each layer owns the resources immediately below it.

Hardware resources should never be controlled simultaneously by multiple
independent components.

------------------------------------------------------------------------

# Design Principles

The Hardware Layer follows the Betabox Platform Design Principles:

-   Single Responsibility
-   Composition over Inheritance
-   Stable Public API
-   Hardware Independence
-   Explicit Behavior
-   Physical Units
-   Exclusive Resource Ownership
-   Safe by Default

------------------------------------------------------------------------

# Future Hardware

Future hardware components may include:

-   Encoder
-   RGB LED
-   IMU

Future hardware interfaces may include:

-   SPI
-   UART

Each new component should include:

-   Documentation
-   Example program
-   API documentation
-   Hardware validation

No hardware abstraction is considered complete until it is documented,
tested, and safe to use.

------------------------------------------------------------------------

# Summary

The Hardware Layer forms the foundation of the Betabox platform.

It isolates hardware-specific implementation details from higher-level
subsystems while providing safe, predictable, and hardware-independent
interfaces.

By exposing physical concepts instead of low-level hardware mechanisms,
the Hardware Layer allows the rest of the platform to remain portable,
maintainable, and easy to teach.
