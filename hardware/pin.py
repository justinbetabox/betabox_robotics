from enum import Enum
from typing import Any, Callable, Optional, Union

from gpiozero import Button, InputDevice, OutputDevice

from .board import BOARD_PINS, DigitalPin
from .exceptions import InvalidModeError, InvalidPinError, PinModeError


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
    Betabox hardware pin abstraction.

    gpiozero is the current backend, but the public API belongs to Betabox.
    """

    OUT = PinMode.OUT
    IN = PinMode.IN

    PULL_UP = Pull.UP
    PULL_DOWN = Pull.DOWN
    PULL_NONE = Pull.NONE

    IRQ_FALLING = Trigger.FALLING
    IRQ_RISING = Trigger.RISING
    IRQ_BOTH = Trigger.BOTH

    BOARD_PINS = BOARD_PINS

    def __init__(
        self,
        pin: Union[int, str, DigitalPin],
        mode: PinMode = OUT,
        pull: Pull = PULL_NONE,
        active_state: Optional[bool] = None,
    ) -> None:
        if isinstance(pin, DigitalPin):
            self.board_name = pin.name
        elif isinstance(pin, str):
            self.board_name = pin
        else:
            self.board_name = None
        self.pin_number = self._resolve_pin(pin)

        self._mode: Optional[PinMode] = None
        self._pull: Optional[Pull] = None
        self._active_state = active_state
        self._device: Optional[Any] = None
        self._bounce_time: Optional[float] = None

        self.set_mode(mode, pull=pull, active_state=active_state)

    def _resolve_pin(self, pin: Union[int, str, DigitalPin]) -> int:
        if isinstance(pin, DigitalPin):
            return pin.value

        if isinstance(pin, str):
            if pin not in self.BOARD_PINS:
                raise InvalidPinError(
                    f'Unknown pin name "{pin}". Valid names: {list(self.BOARD_PINS.keys())}'
                )
            return self.BOARD_PINS[pin]

        if isinstance(pin, int):
            if pin not in self.BOARD_PINS.values():
                raise InvalidPinError(
                    f"Unknown GPIO pin {pin}. Valid pins: {sorted(set(self.BOARD_PINS.values()))}"
                )
            return pin

        raise InvalidPinError(
            "pin must be an int GPIO number, string pin name, or DigitalPin"
        )

    @property
    def mode(self) -> Optional[PinMode]:
        return self._mode

    @property
    def pull(self) -> Optional[Pull]:
        return self._pull

    @property
    def device(self):
        if self._device is None:
            raise RuntimeError("Pin has not been initialized")

        return self._device

    def set_mode(
        self,
        mode: PinMode,
        pull: Pull = PULL_NONE,
        active_state: Optional[bool] = None,
    ) -> None:
        if not isinstance(mode, PinMode):
            raise InvalidModeError(f"mode must be Pin.OUT or Pin.IN, not {mode!r}")

        if not isinstance(pull, Pull):
            raise InvalidModeError(
                f"pull must be Pin.PULL_UP, Pin.PULL_DOWN, or Pin.PULL_NONE, not {pull!r}"
            )

        self.close()

        self._mode = mode
        self._pull = pull
        self._active_state = active_state

        if mode == PinMode.OUT:
            self._device = OutputDevice(self.pin_number)
        else:
            if pull == Pull.UP:
                self._device = InputDevice(
                    self.pin_number, pull_up=True, active_state=None
                )
            elif pull == Pull.DOWN:
                self._device = InputDevice(
                    self.pin_number, pull_up=False, active_state=None
                )
            else:
                self._device = InputDevice(
                    self.pin_number,
                    pull_up=False,
                    active_state=active_state,
                )

    def input(
        self, pull: Pull = PULL_NONE, active_state: Optional[bool] = None
    ) -> None:
        self.set_mode(PinMode.IN, pull=pull, active_state=active_state)

    def output(self) -> None:
        self.set_mode(PinMode.OUT)

    def read(self) -> int:
        if self._mode != PinMode.IN:
            raise PinModeError("Cannot read from a pin that is not configured as input")

        return int(self.device.value)

    def write(self, value: bool) -> int:
        if self._mode != PinMode.OUT:
            raise PinModeError("Cannot write to a pin that is not configured as output")

        if bool(value):
            self.device.on()
            return 1

        self.device.off()
        return 0

    def on(self) -> int:
        return self.write(True)

    def off(self) -> int:
        return self.write(False)

    def high(self) -> int:
        return self.on()

    def low(self) -> int:
        return self.off()

    def toggle(self) -> int:
        if self._mode != PinMode.OUT:
            raise RuntimeError("Cannot toggle a pin that is not configured as output")

        if self.device.value:
            return self.off()

        return self.on()

    def irq(
        self,
        handler: Callable,
        trigger: Trigger = IRQ_FALLING,
        bouncetime: int = 200,
        pull: Pull = PULL_UP,
    ) -> None:
        if not isinstance(trigger, Trigger):
            raise ValueError(
                "trigger must be Pin.IRQ_FALLING, Pin.IRQ_RISING, or Pin.IRQ_BOTH"
            )

        if not isinstance(pull, Pull):
            raise ValueError(
                "pull must be Pin.PULL_UP, Pin.PULL_DOWN, or Pin.PULL_NONE"
            )

        self.close()

        pull_up = True if pull == Pull.UP else False

        self._device = Button(
            pin=self.pin_number,
            pull_up=pull_up,
            bounce_time=bouncetime / 1000,
        )

        self._mode = PinMode.IN
        self._pull = pull
        self._bounce_time = bouncetime / 1000

        if trigger in (Trigger.FALLING, Trigger.BOTH):
            self._device.when_pressed = handler

        if trigger in (Trigger.RISING, Trigger.BOTH):
            self._device.when_released = handler

    def value(self, value: Optional[bool] = None) -> int:
        if value is None:
            return self.read()

        return self.write(value)

    def __call__(self, value: Optional[bool] = None) -> int:
        return self.value(value)

    def name(self) -> str:
        return f"GPIO{self.pin_number}"

    def close(self) -> None:
        if self._device is not None:
            try:
                self._device.close()
            finally:
                self._device = None

    def deinit(self) -> None:
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
