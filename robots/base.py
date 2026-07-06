class RobotBase:
    """
    Base class for Betabox robot platforms.
    """

    def __init__(self):
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        return None

    def deinit(self) -> None:
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return None
