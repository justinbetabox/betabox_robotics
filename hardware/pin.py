from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import ClassVar, Self, cast

from gpiozero import (  # pyright: ignore[reportMissingTypeStubs]
    Button,
    InputDevice,
    OutputDevice,
)

from .board import BOARD_PINS, DigitalPin
from .exceptions import (
    InvalidModeError,
    InvalidPinError,
    PinModeError,
)

PinDevice = InputDevice | OutputDevice | Button
IRQHandler = Callable[[], None]


class PinMode(Enum):
    OUT = "out"
    IN = "in"


class Pull(Enum):
    UP = "up"
    DOWN = "down"
    NONE = "none"


class Trigger(Enum):
    FALLING = "falling"
    RISING = "rising"
    BOTH = "both"


class Pin:
    """
    Betabox digital pin abstraction.

    gpiozero is the current backend, but the public API and lifecycle
    belong to Betabox. A Pin closes only its individual gpiozero device;
    top-level hardware owners manage the process-wide pin factory.
    """

    board_name: str | None
    pin_number: int

    _mode: PinMode | None
    _pull: Pull | None
    _active_state: bool | None
    _device: PinDevice | None
    _bounce_time: float | None

    OUT: ClassVar[PinMode] = PinMode.OUT
    IN: ClassVar[PinMode] = PinMode.IN

    PULL_UP: ClassVar[Pull] = Pull.UP
    PULL_DOWN: ClassVar[Pull] = Pull.DOWN
    PULL_NONE: ClassVar[Pull] = Pull.NONE

    IRQ_FALLING: ClassVar[Trigger] = Trigger.FALLING
    IRQ_RISING: ClassVar[Trigger] = Trigger.RISING
    IRQ_BOTH: ClassVar[Trigger] = Trigger.BOTH

    BOARD_PINS: ClassVar[dict[str, int]] = BOARD_PINS

    def __init__(
        self,
        pin: int | str | DigitalPin,
        mode: PinMode = OUT,
        pull: Pull = PULL_NONE,
        active_state: bool | None = None,
    ) -> None:
        if isinstance(pin, DigitalPin):
            self.board_name = pin.name
        elif isinstance(pin, str):
            self.board_name = pin
        else:
            self.board_name = None

        self.pin_number = self._resolve_pin(pin)

        self._mode = None
        self._pull = None
        self._active_state = None
        self._device = None
        self._bounce_time = None

        self.set_mode(
            mode,
            pull=pull,
            active_state=active_state,
        )

    def _resolve_pin(
        self,
        pin: int | str | DigitalPin,
    ) -> int:
        if isinstance(pin, DigitalPin):
            return int(pin)

        if isinstance(pin, str):
            if pin not in self.BOARD_PINS:
                valid_names = ", ".join(self.BOARD_PINS)

                raise InvalidPinError(
                    f'Unknown pin name "{pin}". Valid names: {valid_names}'
                )

            return self.BOARD_PINS[pin]

        if isinstance(pin, bool):
            raise InvalidPinError(
                "pin must be an int GPIO number, string pin name, or DigitalPin"
            )

        valid_pins = set(self.BOARD_PINS.values())

        if pin not in valid_pins:
            raise InvalidPinError(
                f"Unknown GPIO pin {pin}. Valid pins: {sorted(valid_pins)}"
            )

        return pin

    @property
    def mode(self) -> PinMode | None:
        return self._mode

    @property
    def pull(self) -> Pull | None:
        return self._pull

    @property
    def active_state(self) -> bool | None:
        return self._active_state

    @property
    def bounce_time(self) -> float | None:
        return self._bounce_time

    @property
    def closed(self) -> bool:
        return self._device is None

    @property
    def device(self) -> PinDevice:
        device = self._device

        if device is None:
            raise RuntimeError("Pin has not been initialized or is closed")

        return device

    def _input_device(self) -> InputDevice:
        if self._mode is not PinMode.IN:
            raise PinModeError("Pin is not configured as input")

        return cast(
            InputDevice,
            self.device,
        )

    def _output_device(self) -> OutputDevice:
        if self._mode is not PinMode.OUT:
            raise PinModeError("Pin is not configured as output")

        return cast(
            OutputDevice,
            self.device,
        )

    def set_mode(
        self,
        mode: PinMode,
        pull: Pull = PULL_NONE,
        active_state: bool | None = None,
    ) -> None:
        if mode is PinMode.IN and pull is Pull.NONE and active_state is None:
            raise InvalidModeError("active_state is required when using Pin.PULL_NONE")

        self.close()

        if mode is PinMode.OUT:
            new_device: PinDevice = OutputDevice(self.pin_number)
        elif pull is Pull.UP:
            new_device = InputDevice(
                self.pin_number,
                pull_up=True,
                active_state=None,
            )
        elif pull is Pull.DOWN:
            new_device = InputDevice(
                self.pin_number,
                pull_up=False,
                active_state=None,
            )
        else:
            # gpiozero supports pull_up=None for an externally pulled,
            # floating input, although its installed type information
            # declares this parameter as bool.
            new_device = InputDevice(
                self.pin_number,
                pull_up=None,  # pyright: ignore[reportArgumentType]
                active_state=active_state,
            )

        self._device = new_device
        self._mode = mode
        self._pull = pull
        self._active_state = active_state
        self._bounce_time = None

    def input(
        self,
        pull: Pull = PULL_NONE,
        active_state: bool | None = None,
    ) -> None:
        self.set_mode(
            PinMode.IN,
            pull=pull,
            active_state=active_state,
        )

    def output(self) -> None:
        self.set_mode(PinMode.OUT)

    def read(self) -> int:
        return int(self._input_device().value)

    def write(
        self,
        value: bool,
    ) -> int:
        device = self._output_device()

        if bool(value):
            device.on()
            return 1

        device.off()
        return 0

    def toggle(self) -> int:
        device = self._output_device()

        value = cast(
            bool,
            device.value,
        )

        if value:
            return self.off()

        return self.on()

    def on(self) -> int:
        return self.write(True)

    def off(self) -> int:
        return self.write(False)

    def high(self) -> int:
        return self.on()

    def low(self) -> int:
        return self.off()

    def irq(
        self,
        handler: IRQHandler,
        trigger: Trigger = IRQ_FALLING,
        bouncetime: int = 200,
        pull: Pull = PULL_UP,
    ) -> None:
        if pull is Pull.NONE:
            raise InvalidModeError(
                "interrupt pins require Pin.PULL_UP or Pin.PULL_DOWN"
            )

        if bouncetime < 0:
            raise ValueError("bouncetime cannot be negative")

        self.close()

        bounce_seconds = bouncetime / 1000
        pull_up = pull is Pull.UP

        button = Button(
            pin=self.pin_number,
            pull_up=pull_up,
            bounce_time=bounce_seconds,
        )

        if pull is Pull.UP:
            falling_callback = "when_pressed"
            rising_callback = "when_released"
        else:
            falling_callback = "when_released"
            rising_callback = "when_pressed"

        if trigger in (
            Trigger.FALLING,
            Trigger.BOTH,
        ):
            setattr(
                button,
                falling_callback,
                handler,
            )

        if trigger in (
            Trigger.RISING,
            Trigger.BOTH,
        ):
            setattr(
                button,
                rising_callback,
                handler,
            )

        self._device = button
        self._mode = PinMode.IN
        self._pull = pull
        self._active_state = None
        self._bounce_time = bounce_seconds

    def value(
        self,
        value: bool | None = None,
    ) -> int:
        if value is None:
            return self.read()

        return self.write(value)

    def __call__(
        self,
        value: bool | None = None,
    ) -> int:
        return self.value(value)

    def name(self) -> str:
        return f"GPIO{self.pin_number}"

    def close(self) -> None:
        device = self._device

        try:
            if device is not None:
                device.close()
        finally:
            self._device = None
            self._mode = None
            self._pull = None
            self._active_state = None
            self._bounce_time = None

    def deinit(self) -> None:
        self.close()

    def __enter__(self) -> Self:
        if self.closed:
            raise RuntimeError("Cannot enter a closed Pin")

        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()
