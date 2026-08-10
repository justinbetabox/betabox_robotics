from betabox_robotics.robots.betabox_car import BetaboxCar


class Car(BetaboxCar):
    """
    Backward-compatible name for :class:`BetaboxCar`.

    New code should use ``BetaboxCar`` directly.
    """


__all__ = [
    "Car",
]
