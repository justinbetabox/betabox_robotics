from betabox_robotics.hardware import HardwareError


class SensorError(HardwareError):
    """Base exception for sensor subsystem failures."""

class SensorsError(SensorError):
    """Raised when the combined Sensors subsystem fails."""

class BatteryError(SensorError):
    """Raised when a battery sensor operation fails."""


class GrayscaleError(SensorError):
    """Raised when a grayscale sensor operation fails."""


class UltrasonicError(SensorError):
    """Base exception for ultrasonic sensor failures."""


class UltrasonicTimeoutError(UltrasonicError):
    """Raised when no valid echo is received before timeout."""


class UltrasonicReadError(UltrasonicError):
    """Raised when an ultrasonic pulse cannot be measured."""
