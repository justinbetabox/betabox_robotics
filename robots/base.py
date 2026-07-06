from .capabilities import RobotCapability


class RobotBase:
    """
    Base class for Betabox robot platforms.
    """

    capabilities: set[RobotCapability] = set()

    def __init__(self) -> None:
        self._started = False
        self._closed = False

    @property
    def started(self) -> bool:
        return self._started

    @property
    def closed(self) -> bool:
        return self._closed

    def has_capability(self, capability: RobotCapability | str) -> bool:
        if isinstance(capability, str):
            capability = RobotCapability(capability)

        return capability in self.capabilities

    def capability_names(self) -> list[str]:
        return sorted(capability.value for capability in self.capabilities)

    def start(self) -> None:
        if self.closed:
            raise RuntimeError("cannot start a closed robot")

        self._started = True

    def close(self) -> None:
        if self.closed:
            return

        self._started = False
        self._closed = True

    def deinit(self) -> None:
        self.close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return None
