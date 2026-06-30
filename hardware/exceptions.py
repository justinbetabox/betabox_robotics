class HardwareError(Exception):
    """Base exception for Betabox hardware errors."""


class InvalidPinError(HardwareError):
    """Raised when a pin name or pin number is invalid."""


class InvalidModeError(HardwareError):
    """Raised when a hardware mode value is invalid."""


class PinModeError(HardwareError):
    """Raised when an operation is not allowed for the pin's current mode."""
