from __future__ import annotations

from pathlib import Path


DEVICE_TREE_SERIAL_PATH = Path(
    "/sys/firmware/devicetree/base/serial-number"
)

CPUINFO_PATH = Path("/proc/cpuinfo")


def get_serial() -> str | None:
    """
    Return the Raspberry Pi hardware serial number.

    The device-tree serial is preferred. /proc/cpuinfo is used as a
    compatibility fallback.
    """

    if DEVICE_TREE_SERIAL_PATH.exists():
        serial = (
            DEVICE_TREE_SERIAL_PATH
            .read_text(
                encoding="utf-8",
                errors="ignore",
            )
            .replace("\x00", "")
            .strip()
        )

        if serial:
            return serial

    if CPUINFO_PATH.exists():
        lines = CPUINFO_PATH.read_text(
            encoding="utf-8",
            errors="ignore",
        ).splitlines()

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

    if length <= 0:
        raise ValueError(
            "length must be greater than 0"
        )

    serial = get_serial()

    if serial is None:
        return fallback

    return serial[-length:]


def identity_name(
    prefix: str,
    *,
    suffix_length: int = 4,
    fallback: str | None = None,
) -> str | None:
    """
    Build an identity name such as Betabox-7eea.
    """

    cleaned_prefix = prefix.strip()

    if not cleaned_prefix:
        raise ValueError(
            "prefix cannot be empty"
        )

    suffix = serial_suffix(
        suffix_length,
        fallback=fallback,
    )

    if suffix is None:
        return None

    return f"{cleaned_prefix}-{suffix}"
