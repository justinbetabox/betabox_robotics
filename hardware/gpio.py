from __future__ import annotations

from gpiozero import Device


def close_gpio_factory() -> None:
    """
    Close gpiozero's process-wide pin factory.

    This releases lgpio's gpiochip handle and allows another process to
    acquire the robot GPIO lines.
    """

    factory = Device.pin_factory

    if factory is None:
        return

    try:
        factory.close()
    finally:
        Device.pin_factory = None
