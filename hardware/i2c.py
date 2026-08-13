from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable, Sequence
from functools import wraps
from typing import ClassVar, Concatenate, ParamSpec, Self, TypeVar

from smbus2 import SMBus

from .exceptions import HardwareError


class I2CError(HardwareError):
    """Raised when an I2C operation fails."""


P = ParamSpec("P")
R = TypeVar("R")


def retry_i2c(
    func: Callable[Concatenate[I2C, P], R],
) -> Callable[Concatenate[I2C, P], R]:
    """Retry an I2C operation when the SMBus backend raises OSError."""

    @wraps(func)
    def wrapper(
        self: I2C,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        last_error: OSError | None = None

        for attempt in range(
            1,
            self.retry_count + 1,
        ):
            try:
                return func(
                    self,
                    *args,
                    **kwargs,
                )

            except OSError as exc:
                last_error = exc

                self.logger.debug(
                    "I2C OSError in %s (attempt %d/%d): %s",
                    func.__name__,
                    attempt,
                    self.retry_count,
                    exc,
                )

        raise I2CError(
            f"I2C operation failed after {self.retry_count} attempts"
        ) from last_error

    return wrapper


class I2C:
    """Betabox I2C device abstraction."""

    logger: logging.Logger
    bus_number: int
    retry_count: int
    address: int | None

    _smbus: SMBus | None

    DEFAULT_RETRY_COUNT: ClassVar[int] = 5

    def __init__(
        self,
        address: int | Sequence[int] | None = None,
        bus: int = 1,
        retry_count: int = DEFAULT_RETRY_COUNT,
    ) -> None:
        if bus < 0:
            raise ValueError("bus cannot be negative")

        if retry_count < 1:
            raise ValueError("retry_count must be at least 1")

        normalized_address = self._validate_address_argument(address)

        self.logger = logging.getLogger(__name__)

        self.bus_number = bus
        self.retry_count = retry_count
        self.address = None
        self._smbus = None

        try:
            self._smbus = SMBus(self.bus_number)

            self.address = self._select_address(normalized_address)

        except (
            HardwareError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ):
            self.close()
            raise

    @staticmethod
    def _validate_address(
        address: object,
    ) -> int:
        if isinstance(address, bool) or not isinstance(
            address,
            int,
        ):
            raise TypeError("I2C addresses must be integers")

        if not 0 <= address <= 0x7F:
            raise ValueError("I2C address must be between 0x00 and 0x7F")

        return address

    @classmethod
    def _validate_address_argument(
        cls,
        address: int | Sequence[int] | None,
    ) -> int | list[int] | None:
        if address is None:
            return None

        if isinstance(address, Sequence) and not isinstance(
            address,
            str | bytes | bytearray,
        ):
            if not address:
                raise ValueError("address candidate sequence cannot be empty")

            return [cls._validate_address(candidate) for candidate in address]

        return cls._validate_address(address)

    def _select_address(
        self,
        address: int | list[int] | None,
    ) -> int | None:
        if not isinstance(address, list):
            return address

        connected_devices = self.scan()

        for candidate in address:
            if candidate in connected_devices:
                return candidate

        # Preserve the existing compatibility behavior for now:
        # when no candidate is detected, use the first configured address.
        return address[0]

    def _bus(self) -> SMBus:
        bus = self._smbus

        if bus is None:
            raise I2CError("I2C bus is closed")

        return bus

    def _address(self) -> int:
        address = self.address

        if address is None:
            raise I2CError("I2C address is not set")

        return address

    @property
    def closed(self) -> bool:
        return self._smbus is None

    def close(self) -> None:
        bus = self._smbus

        try:
            if bus is not None:
                bus.close()
        finally:
            self._smbus = None

    @retry_i2c
    def _write_byte(self, data: int) -> None:
        self.logger.debug("_write_byte: [0x%02X]", data)
        self._bus().write_byte(self._address(), data)

    @retry_i2c
    def _write_byte_data(self, reg: int, data: int) -> None:
        self.logger.debug("_write_byte_data: [0x%02X] [0x%02X]", reg, data)
        self._bus().write_byte_data(self._address(), reg, data)

    @retry_i2c
    def _write_word_data(self, reg: int, data: int) -> None:
        self.logger.debug("_write_word_data: [0x%02X] [0x%04X]", reg, data)
        self._bus().write_word_data(self._address(), reg, data)

    @retry_i2c
    def _write_i2c_block_data(self, reg: int, data: list[int]) -> None:
        self.logger.debug(
            "_write_i2c_block_data: [0x%02X] %s",
            reg,
            [f"0x{i:02X}" for i in data],
        )
        self._bus().write_i2c_block_data(self._address(), reg, data)

    @retry_i2c
    def _read_byte(self) -> int:
        result = self._bus().read_byte(self._address())
        self.logger.debug("_read_byte: [0x%02X]", result)
        return result

    @retry_i2c
    def _read_byte_data(self, reg: int) -> int:
        result = self._bus().read_byte_data(self._address(), reg)
        self.logger.debug("_read_byte_data: [0x%02X] [0x%02X]", reg, result)
        return result

    @retry_i2c
    def _read_word_data(self, reg: int) -> list[int]:
        result = self._bus().read_word_data(self._address(), reg)
        result_list = [result & 0xFF, (result >> 8) & 0xFF]
        self.logger.debug("_read_word_data: [0x%02X] [0x%04X]", reg, result)
        return result_list

    @retry_i2c
    def _read_i2c_block_data(self, reg: int, length: int) -> list[int]:
        result = self._bus().read_i2c_block_data(self._address(), reg, length)
        self.logger.debug(
            "_read_i2c_block_data: [0x%02X] %s",
            reg,
            [f"0x{i:02X}" for i in result],
        )
        return result

    def scan(self) -> list[int]:
        try:
            result = subprocess.run(
                [
                    "i2cdetect",
                    "-y",
                    str(self.bus_number),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            raise I2CError("Unable to run i2cdetect") from exc

        if result.returncode != 0:
            raise I2CError(result.stderr.strip() or "i2cdetect failed")

        addresses: list[int] = []

        for line in result.stdout.splitlines():
            if ":" not in line:
                continue

            row_text, values_text = line.split(
                ":",
                1,
            )

            try:
                row_start = int(
                    row_text.strip(),
                    16,
                )
            except ValueError:
                continue

            for offset, value in enumerate(values_text.split()):
                if value == "--":
                    continue

                if value == "UU":
                    addresses.append(row_start + offset)
                    continue

                try:
                    addresses.append(int(value, 16))
                except ValueError:
                    continue

        addresses = sorted(set(addresses))

        self.logger.debug(
            "Connected I2C devices: %s",
            [f"0x{address:02X}" for address in addresses],
        )

        return addresses

    def is_ready(self) -> bool:
        if self.address is None:
            return False

        return self.address in self.scan()

    def is_available(self) -> bool:
        return self.is_ready()

    def write(
        self,
        data: int | list[int] | bytearray,
    ) -> None:
        data_all = self._normalize_write_data(data)

        if len(data_all) == 1:
            self._write_byte(data_all[0])
        elif len(data_all) == 2:
            self._write_byte_data(data_all[0], data_all[1])
        elif len(data_all) == 3:
            reg = data_all[0]
            value = (data_all[2] << 8) + data_all[1]
            self._write_word_data(reg, value)
        else:
            reg = data_all[0]
            self._write_i2c_block_data(reg, list(data_all[1:]))

    def read(
        self,
        length: int = 1,
    ) -> list[int]:
        if length <= 0:
            raise ValueError("length must be greater than 0")

        return [self._read_byte() for _ in range(length)]

    def mem_write(
        self,
        data: int | list[int] | bytearray,
        memaddr: int,
    ) -> None:
        data_all = self._normalize_write_data(data)

        self._write_i2c_block_data(
            memaddr,
            data_all,
        )

    def mem_read(
        self,
        length: int,
        memaddr: int,
    ) -> list[int]:
        if length <= 0:
            raise ValueError("length must be greater than 0")

        return self._read_i2c_block_data(
            memaddr,
            length,
        )

    @staticmethod
    def _validate_byte(
        value: object,
    ) -> int:
        if isinstance(value, bool) or not isinstance(
            value,
            int,
        ):
            raise TypeError("I2C data values must be integers")

        if not 0 <= value <= 0xFF:
            raise ValueError("I2C data values must be between 0 and 255")

        return value

    def _normalize_write_data(
        self,
        data: int | list[int] | bytearray,
    ) -> list[int]:
        if isinstance(data, bool):
            raise TypeError("write data must be an int, list, or bytearray")

        if isinstance(data, int):
            if data < 0:
                raise ValueError("data integer must be non-negative")

            if data == 0:
                return [0]

            values: list[int] = []

            while data:
                values.append(data & 0xFF)
                data >>= 8

            return values

        if isinstance(data, bytearray):
            values = list(data)
        else:
            values = [self._validate_byte(value) for value in data]

        if not values:
            raise ValueError("write data cannot be empty")

        return values

    def __enter__(self) -> Self:
        if self.closed:
            raise I2CError("Cannot enter a closed I2C bus")

        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()
