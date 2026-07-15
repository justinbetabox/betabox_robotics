class BetaboxError(Exception):
    """Base exception for Betabox Robotics."""


class RobotBusyError(BetaboxError):
    """The robot is currently owned by another application."""
