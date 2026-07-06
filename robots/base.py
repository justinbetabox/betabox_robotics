class RobotBase:
    """
    Base class for Betabox robot platforms.
    """

    def close(self) -> None:
        return None

    def deinit(self) -> None:
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return None
