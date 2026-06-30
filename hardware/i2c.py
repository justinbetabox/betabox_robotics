import logging
import subprocess
from functools import wraps
from typing import Any, Callable, List, Optional, ParamSpec, TypeVar, Union

from smbus2 import SMBus

from .exceptions import HardwareError


class I2CError(HardwareError):
    """Raised when an I2C operation fails."""


P = ParamSpec("P")
R = TypeVar("R")


def retry_i2c(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        last_error: OSError | None = None

        for _ in range(self.retry_count):
            try:
                return func(self, *args, **kwargs)
            except OSError as error:
                last_error = error
                self.logger.debug("I2C OSError in %s: %s", func.__name__, error)

        raise I2CError(
            f"I2C operation failed after {self.retry_count} retries"
        ) from last_error

    return wrapper


class I2C:
    """
    Betabox I2C device abstraction.
    """

    DEFAULT_RETRY_COUNT = 5

    def __init__(
        self,
        address: Union[int, List[int], None] = None,
        bus: int = 1,
        retry_count: int = DEFAULT_RETRY_COUNT,
    ) -> None:
        self.logger = logging.getLogger(__name__)

        self.bus_number = bus
        self.retry_count = retry_count
        self._smbus: Optional[SMBus] = SMBus(self.bus_number)

        if isinstance(address, list):
            connected_devices = self.scan()
            for candidate in address:
                if candidate in connected_devices:
                    self.address = candidate
                    break
            else:
                self.address = address[0]
        else:
            self.address = address

    def _bus(self) -> SMBus:
        if self._smbus is None:
            raise I2CError("I2C bus is closed")

        return self._smbus

    def _address(self) -> int:
        if self.address is None:
            raise I2CError("I2C address is not set")

        return self.address

    def close(self) -> None:
        if self._smbus is not None:
            self._smbus.close()
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
    def _write_i2c_block_data(self, reg: int, data: List[int]) -> None:
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
    def _read_word_data(self, reg: int) -> List[int]:
        result = self._bus().read_word_data(self._address(), reg)
        result_list = [result & 0xFF, (result >> 8) & 0xFF]
        self.logger.debug("_read_word_data: [0x%02X] [0x%04X]", reg, result)
        return result_list

    @retry_i2c
    def _read_i2c_block_data(self, reg: int, length: int) -> List[int]:
        result = self._bus().read_i2c_block_data(self._address(), reg, length)
        self.logger.debug(
            "_read_i2c_block_data: [0x%02X] %s",
            reg,
            [f"0x{i:02X}" for i in result],
        )
        return result

    def scan(self) -> List[int]:
        result = subprocess.run(
            ["i2cdetect", "-y", str(self.bus_number)],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise I2CError(result.stderr.strip() or "i2cdetect failed")

        addresses: List[int] = []

        for line in result.stdout.splitlines()[1:]:
            if not line or ":" not in line:
                continue

            _, values = line.split(":", 1)

            for value in values.strip().split():
                if value != "--":
                    addresses.append(int(value, 16))

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

    def write(self, data: Union[int, List[int], bytearray]) -> None:
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

    def read(self, length: int = 1) -> List[int]:
        if not isinstance(length, int):
            raise ValueError(f"length must be int, not {type(length)}")

        if length <= 0:
            raise ValueError("length must be greater than 0")

        return [self._read_byte() for _ in range(length)]

    def mem_write(self, data: Union[int, List[int], bytearray], memaddr: int) -> None:
        data_all = self._normalize_write_data(data)
        self._write_i2c_block_data(memaddr, data_all)

    def mem_read(self, length: int, memaddr: int) -> List[int]:
        if not isinstance(length, int):
            raise ValueError(f"length must be int, not {type(length)}")

        if length <= 0:
            raise ValueError("length must be greater than 0")

        return self._read_i2c_block_data(memaddr, length)

    def _normalize_write_data(
        self, data: Union[int, List[int], bytearray]
    ) -> List[int]:
        if isinstance(data, bytearray):
            return list(data)

        if isinstance(data, list):
            return data

        if isinstance(data, int):
            if data < 0:
                raise ValueError("data integer must be non-negative")

            if data == 0:
                return [0]

            data_all: List[int] = []

            while data > 0:
                data_all.append(data & 0xFF)
                data //= 256

            return data_all

        raise ValueError(
            f"write data must be int, list, or bytearray, not {type(data)}"
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
