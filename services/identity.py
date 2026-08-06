from __future__ import annotations

from pathlib import Path

DEVICE_TREE_SERIAL_PATH = Path("/sys/firmware/devicetree/base/serial-number")

CPUINFO_PATH = Path("/proc/cpuinfo")


def _validate_length(
    value: object,
) -> int:
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError("length must be an integer")

    if value <= 0:
        raise ValueError("length must be greater than 0")

    return value


def _validate_prefix(
    value: object,
) -> str:
    if not isinstance(value, str):
        raise TypeError("prefix must be a string")

    result = value.strip()

    if not result:
        raise ValueError("prefix cannot be empty")

    return result


def _validate_optional_string(
    value: object,
    *,
    name: str,
) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string or None")

    result = value.strip()

    if not result:
        raise ValueError(f"{name} cannot be empty")

    return result


def get_serial() -> str | None:
    """
    Return the Raspberry Pi hardware serial number.

    The device-tree serial is preferred. /proc/cpuinfo is used as a
    compatibility fallback.
    """

    if DEVICE_TREE_SERIAL_PATH.is_file():
        try:
            serial = (
                DEVICE_TREE_SERIAL_PATH.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
                .replace("\x00", "")
                .strip()
            )
        except OSError:
            serial = ""

        if serial:
            return serial

    if CPUINFO_PATH.is_file():
        try:
            lines = CPUINFO_PATH.read_text(
                encoding="utf-8",
                errors="ignore",
            ).splitlines()
        except OSError:
            lines = ()

        for line in lines:
            if not line.startswith("Serial"):
                continue

            _, separator, value = line.partition(":")

            if not separator:
                continue

            serial = value.strip()

            if serial:
                return serial

    return None


def serial_suffix(
    length: int = 4,
    *,
    fallback: str | None = None,
) -> str | None:
    """
    Return the final characters of the Raspberry Pi serial number.

    If the serial cannot be determined, return the supplied fallback.
    """

    validated_length = _validate_length(length)
    validated_fallback = _validate_optional_string(
        fallback,
        name="fallback",
    )

    serial = get_serial()

    if serial is None:
        return validated_fallback

    return serial[-validated_length:]


def identity_name(
    prefix: str,
    *,
    suffix_length: int = 4,
    fallback: str | None = None,
) -> str | None:
    """
    Build an identity name such as Betabox-7eea.
    """

    cleaned_prefix = _validate_prefix(prefix)
    validated_fallback = _validate_optional_string(
        fallback,
        name="fallback",
    )

    suffix = serial_suffix(
        suffix_length,
        fallback=validated_fallback,
    )

    if suffix is None:
        return None

    return f"{cleaned_prefix}-{suffix}"
