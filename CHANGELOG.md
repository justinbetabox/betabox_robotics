# CHANGELOG

## 0.1.0 (Development)

### Added

-   New Betabox hardware architecture.
-   Backend-independent Pin abstraction.
-   Backend-independent I2C abstraction.
-   PWM rewritten using composition.
-   Servo rewritten using composition.
-   Pins namespace (`Pins.D0`, `Pins.P0`, etc.).
-   Hardware exceptions.
-   Versioning support.
-   Project documentation structure.
-   Tests and examples directory structure.
-   Motor hardware abstraction.
-   Drive subsystem.
-   Drive default hardware factory.
-   Drive hardware tests and examples.
-   ADC hardware abstraction.
-   Analog channel support through `Pins.A0` to `Pins.A7`.
-   ADC hardware test and demo.
-   Ultrasonic sensor abstraction.
-   Ultrasonic hardware test and demo.
-   Sensors subsystem wrapper.
-   Grayscale sensor abstraction.
-   Grayscale floor/line calibration support.
-   Grayscale hardware test and demo.

### Changed

-   Replaced inheritance with composition throughout the hardware layer.
-   Introduced explicit hardware state management.
-   Established stable Betabox API philosophy.
