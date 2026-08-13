from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from betabox_robotics.hardware import (
    AnalogChannel,
    DigitalPin,
    PWMChannel,
)


def _validate_number(
    value: object,
    *,
    name: str,
) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        int | float,
    ):
        raise TypeError(f"{name} must be a number")

    result = float(value)

    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")

    return result


def _validate_positive_number(
    value: object,
    *,
    name: str,
) -> float:
    result = _validate_number(
        value,
        name=name,
    )

    if result <= 0:
        raise ValueError(f"{name} must be greater than zero")

    return result


def _validate_string(
    value: object,
    *,
    name: str,
    allow_none: bool = False,
) -> str | None:
    if value is None and allow_none:
        return None

    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")

    result = value.strip()

    if not result:
        raise ValueError(f"{name} cannot be empty")

    return result


def _validate_bool(
    value: object,
    *,
    name: str,
) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a boolean")

    return value


@dataclass(frozen=True, slots=True)
class MotorConfig:
    pwm: PWMChannel
    direction: DigitalPin
    reversed: bool = False
    trim: float = 1.0

    def __post_init__(self) -> None:
        reversed_value = _validate_bool(
            self.reversed,
            name="reversed",
        )
        trim = _validate_number(
            self.trim,
            name="trim",
        )

        if not 0.0 <= trim <= 1.0:
            raise ValueError("trim must be between 0.0 and 1.0")

        object.__setattr__(
            self,
            "reversed",
            reversed_value,
        )
        object.__setattr__(
            self,
            "trim",
            trim,
        )


@dataclass(frozen=True, slots=True)
class SteeringConfig:
    servo: PWMChannel
    min_angle: float = -30.0
    max_angle: float = 30.0

    def __post_init__(self) -> None:
        min_angle = _validate_number(
            self.min_angle,
            name="min_angle",
        )
        max_angle = _validate_number(
            self.max_angle,
            name="max_angle",
        )

        if min_angle >= max_angle:
            raise ValueError("min_angle must be less than max_angle")

        object.__setattr__(
            self,
            "min_angle",
            min_angle,
        )
        object.__setattr__(
            self,
            "max_angle",
            max_angle,
        )


@dataclass(frozen=True, slots=True)
class CameraMountConfig:
    pan_servo: PWMChannel
    tilt_servo: PWMChannel

    pan_min_angle: float = -45.0
    pan_max_angle: float = 45.0

    tilt_min_angle: float = -30.0
    tilt_max_angle: float = 45.0

    pan_center: float = 0.0
    tilt_center: float = 0.0

    pan_reversed: bool = False
    tilt_reversed: bool = False

    def __post_init__(self) -> None:
        pan_min_angle = _validate_number(
            self.pan_min_angle,
            name="pan_min_angle",
        )
        pan_max_angle = _validate_number(
            self.pan_max_angle,
            name="pan_max_angle",
        )
        tilt_min_angle = _validate_number(
            self.tilt_min_angle,
            name="tilt_min_angle",
        )
        tilt_max_angle = _validate_number(
            self.tilt_max_angle,
            name="tilt_max_angle",
        )
        pan_center = _validate_number(
            self.pan_center,
            name="pan_center",
        )
        tilt_center = _validate_number(
            self.tilt_center,
            name="tilt_center",
        )
        pan_reversed = _validate_bool(
            self.pan_reversed,
            name="pan_reversed",
        )
        tilt_reversed = _validate_bool(
            self.tilt_reversed,
            name="tilt_reversed",
        )

        if pan_min_angle >= pan_max_angle:
            raise ValueError("pan_min_angle must be less than pan_max_angle")

        if tilt_min_angle >= tilt_max_angle:
            raise ValueError("tilt_min_angle must be less than tilt_max_angle")

        if not (pan_min_angle <= pan_center <= pan_max_angle):
            raise ValueError("pan_center must be within the pan angle range")

        if not (tilt_min_angle <= tilt_center <= tilt_max_angle):
            raise ValueError("tilt_center must be within the tilt angle range")

        object.__setattr__(
            self,
            "pan_min_angle",
            pan_min_angle,
        )
        object.__setattr__(
            self,
            "pan_max_angle",
            pan_max_angle,
        )
        object.__setattr__(
            self,
            "tilt_min_angle",
            tilt_min_angle,
        )
        object.__setattr__(
            self,
            "tilt_max_angle",
            tilt_max_angle,
        )
        object.__setattr__(
            self,
            "pan_center",
            pan_center,
        )
        object.__setattr__(
            self,
            "tilt_center",
            tilt_center,
        )
        object.__setattr__(
            self,
            "pan_reversed",
            pan_reversed,
        )
        object.__setattr__(
            self,
            "tilt_reversed",
            tilt_reversed,
        )


@dataclass(frozen=True, slots=True)
class DriveConfig:
    left_motor: MotorConfig
    right_motor: MotorConfig
    steering: SteeringConfig


@dataclass(frozen=True, slots=True)
class UltrasonicConfig:
    trigger: DigitalPin
    echo: DigitalPin
    timeout: float = 0.02

    def __post_init__(self) -> None:
        timeout = _validate_positive_number(
            self.timeout,
            name="timeout",
        )

        object.__setattr__(
            self,
            "timeout",
            timeout,
        )


@dataclass(frozen=True, slots=True)
class GrayscaleConfig:
    left: AnalogChannel
    middle: AnalogChannel
    right: AnalogChannel
    reference: tuple[int, int, int] = (
        1000,
        1000,
        1000,
    )

    def __post_init__(self) -> None:
        if len(self.reference) != 3:
            raise ValueError("reference must contain exactly 3 values")

        reference: list[int] = []

        for value in self.reference:
            if value < 0:
                raise ValueError("reference values cannot be negative")

            reference.append(value)

        object.__setattr__(
            self,
            "reference",
            (
                reference[0],
                reference[1],
                reference[2],
            ),
        )


@dataclass(frozen=True, slots=True)
class BatteryConfig:
    channel: AnalogChannel
    scale: float = 3.0
    low_voltage: float = 6.6
    critical_voltage: float = 6.2

    def __post_init__(self) -> None:
        scale = _validate_positive_number(
            self.scale,
            name="scale",
        )
        low_voltage = _validate_positive_number(
            self.low_voltage,
            name="low_voltage",
        )
        critical_voltage = _validate_positive_number(
            self.critical_voltage,
            name="critical_voltage",
        )

        if critical_voltage >= low_voltage:
            raise ValueError("critical_voltage must be less than low_voltage")

        object.__setattr__(
            self,
            "scale",
            scale,
        )
        object.__setattr__(
            self,
            "low_voltage",
            low_voltage,
        )
        object.__setattr__(
            self,
            "critical_voltage",
            critical_voltage,
        )


@dataclass(frozen=True, slots=True)
class SensorsConfig:
    ultrasonic: UltrasonicConfig
    grayscale: GrayscaleConfig
    battery: BatteryConfig


@dataclass(frozen=True, slots=True)
class VisionConfig:
    service_url: str = "http://127.0.0.1:8080"
    request_timeout: float = 10.0

    def __post_init__(self) -> None:
        service_url = _validate_string(
            self.service_url,
            name="service_url",
        )
        request_timeout = _validate_positive_number(
            self.request_timeout,
            name="request_timeout",
        )

        object.__setattr__(
            self,
            "service_url",
            service_url,
        )
        object.__setattr__(
            self,
            "request_timeout",
            request_timeout,
        )


@dataclass(frozen=True, slots=True)
class AudioConfig:
    speech_engine: str = "auto"
    speech_language: str = "en-US"
    piper_model: str | None = None
    piper_voice: str = "en_US-amy-low"
    preferred_output_device: str = "snd_rpi_hifiberry_dac"
    sample_rate: int = 44100
    auto_amp: bool = True
    keep_amp_enabled: bool = False
    speech_volume: float = 1.0

    def __post_init__(self) -> None:
        speech_engine = _validate_string(
            self.speech_engine,
            name="speech_engine",
        )
        speech_language = _validate_string(
            self.speech_language,
            name="speech_language",
        )
        piper_model = _validate_string(
            self.piper_model,
            name="piper_model",
            allow_none=True,
        )
        piper_voice = _validate_string(
            self.piper_voice,
            name="piper_voice",
        )
        preferred_output_device = _validate_string(
            self.preferred_output_device,
            name="preferred_output_device",
        )

        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be greater than zero")

        auto_amp = _validate_bool(
            self.auto_amp,
            name="auto_amp",
        )
        keep_amp_enabled = _validate_bool(
            self.keep_amp_enabled,
            name="keep_amp_enabled",
        )
        speech_volume = _validate_number(
            self.speech_volume,
            name="speech_volume",
        )

        if not 0.0 <= speech_volume <= 1.0:
            raise ValueError("speech_volume must be between 0.0 and 1.0")

        object.__setattr__(
            self,
            "speech_engine",
            speech_engine,
        )
        object.__setattr__(
            self,
            "speech_language",
            speech_language,
        )
        object.__setattr__(
            self,
            "piper_model",
            piper_model,
        )
        object.__setattr__(
            self,
            "piper_voice",
            piper_voice,
        )
        object.__setattr__(
            self,
            "preferred_output_device",
            preferred_output_device,
        )
        object.__setattr__(
            self,
            "auto_amp",
            auto_amp,
        )
        object.__setattr__(
            self,
            "keep_amp_enabled",
            keep_amp_enabled,
        )
        object.__setattr__(
            self,
            "speech_volume",
            speech_volume,
        )


@dataclass(frozen=True, slots=True)
class SystemConfig:
    media_root: str | Path | None = None

    def __post_init__(self) -> None:
        if self.media_root is None:
            return

        object.__setattr__(
            self,
            "media_root",
            Path(self.media_root).expanduser(),
        )


@dataclass(frozen=True, slots=True)
class RobotConfig:
    drive: DriveConfig
    camera_mount: CameraMountConfig
    sensors: SensorsConfig
    vision: VisionConfig = field(default_factory=VisionConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    system: SystemConfig = field(default_factory=SystemConfig)
