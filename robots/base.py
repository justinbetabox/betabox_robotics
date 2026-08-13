from __future__ import annotations

from typing import ClassVar, Self

from .capabilities import RobotCapability
from .exceptions import RobotLifecycleError


class RobotBase:
    """
    Base lifecycle contract for Betabox robot platforms.
    """

    capabilities: ClassVar[frozenset[RobotCapability]] = frozenset()

    _started: bool
    _closed: bool

    def __init__(self) -> None:
        self._started = False
        self._closed = False

    @property
    def started(self) -> bool:
        return self._started

    @property
    def closed(self) -> bool:
        return self._closed

    def require_open(self) -> None:
        if self._closed:
            raise RobotLifecycleError("robot is closed")

    def require_started(self) -> None:
        self.require_open()

        if not self._started:
            raise RobotLifecycleError("robot is not started")

    def has_capability(
        self,
        capability: RobotCapability | str,
    ) -> bool:
        if isinstance(
            capability,
            RobotCapability,
        ):
            capability_value = capability

        else:
            normalized = capability.strip().casefold()

            if not normalized:
                raise ValueError("capability cannot be empty")

            try:
                capability_value = RobotCapability(normalized)
            except ValueError as exc:
                raise ValueError(f"unknown robot capability: {capability}") from exc

        return capability_value in self.capabilities

    def capability_names(
        self,
    ) -> tuple[str, ...]:
        return tuple(sorted(capability.value for capability in self.capabilities))

    def start(self) -> None:
        self.require_open()

        if self._started:
            return

        self._started = True

    def stop_all(self) -> None:
        self.require_open()
        self._started = False

    def close(self) -> None:
        if self._closed:
            return

        if self._started:
            self.stop_all()

        self._started = False
        self._closed = True

    def deinit(self) -> None:
        self.close()

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()
