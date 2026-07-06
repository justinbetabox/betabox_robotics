from betabox_robotics.robots.betabox_car import BETABOX_CAR, BetaboxCar, RobotConfig


class Robot:
    """
    Public robot factory.

    Currently defaults to the Betabox Car platform.
    """

    @classmethod
    def default(cls) -> BetaboxCar:
        return BetaboxCar(BETABOX_CAR)

    @classmethod
    def from_config(cls, config: RobotConfig) -> BetaboxCar:
        return BetaboxCar(config)
