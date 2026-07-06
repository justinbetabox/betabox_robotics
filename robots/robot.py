from .base import RobotBase


class Robot(RobotBase):
    """
    Base class for all Betabox robot platforms.

    Concrete robot types should inherit from this class through a more
    specific robot contract, such as CarRobot.
    """
