from __future__ import annotations


class RobotRuntimeError(RuntimeError):
    """Base error for Betabox robot runtime failures."""


class RobotRuntimeUnavailableError(RobotRuntimeError):
    """The Betabox robot runtime is unavailable."""


class RobotRuntimeProtocolError(RobotRuntimeError):
    """The Betabox robot runtime protocol is invalid."""


class RobotRuntimeControlError(RobotRuntimeError):
    """A robot runtime control operation failed."""


class RobotRuntimeControlBusyError(RobotRuntimeControlError):
    """Robot control is already owned by another client."""
