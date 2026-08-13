from __future__ import annotations

from betabox_robotics.robots.betabox_car import BetaboxCar
from betabox_robotics.robots.config import RobotConfig


class Robot:
    """
    Public robot factory.

    Currently creates the Betabox Car platform.
    """

    @classmethod
    def default(
        cls,
    ) -> BetaboxCar:
        return BetaboxCar()

    @classmethod
    def from_config(
        cls,
        config: RobotConfig,
    ) -> BetaboxCar:
        return BetaboxCar(config)


__all__ = [
    "Robot",
]
