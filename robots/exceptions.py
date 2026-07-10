class RobotError(Exception):
    """Base exception for Robot API failures."""


class RobotLifecycleError(RobotError):
    """Raised when a robot operation violates its lifecycle."""
