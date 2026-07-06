from .robot import Robot


class CarRobot(Robot):
    """
    Base class for car-style Betabox robots.

    Concrete car implementations are responsible for constructing their
    hardware-backed subsystems.
    """
