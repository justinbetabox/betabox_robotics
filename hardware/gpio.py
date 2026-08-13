from __future__ import annotations

from typing import Protocol, cast

from gpiozero import Device  # pyright: ignore[reportMissingTypeStubs]


class _GPIOFactory(Protocol):
    def close(self) -> None: ...


def close_gpio_factory() -> None:
    """
    Close gpiozero's process-wide pin factory.

    This releases lgpio's gpiochip handle and allows another process to
    acquire the robot GPIO lines. Call this only when the current process
    has finished using all gpiozero-backed hardware.
    """

    factory = cast(
        _GPIOFactory | None,
        Device.pin_factory,
    )

    if factory is None:
        return

    try:
        factory.close()
    finally:
        Device.pin_factory = None
