from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TypedDict, cast

CALIBRATION_VERSION = 1


class SteeringCalibrationDict(TypedDict):
    offset: float


class MotorCalibrationDict(TypedDict):
    left_trim: float
    right_trim: float


class CameraMountCalibrationDict(TypedDict):
    pan_offset: float
    tilt_offset: float


class GrayscaleCalibrationDict(TypedDict):
    floor: tuple[float, float, float] | None
    line: tuple[float, float, float] | None


class RobotCalibrationDict(TypedDict):
    version: int
    camera_mount: CameraMountCalibrationDict
    steering: SteeringCalibrationDict
    motors: MotorCalibrationDict
    grayscale: GrayscaleCalibrationDict


def _float_value(
    value: object,
    *,
    field_name: str,
    default: float | None = None,
) -> float:
    if value is None:
        if default is None:
            raise ValueError(f"{field_name} must be a number")

        return _float_value(
            default,
            field_name=field_name,
        )

    if isinstance(value, bool) or not isinstance(
        value,
        int | float | str,
    ):
        raise TypeError(f"{field_name} must be a number")

    try:
        result = float(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a number") from exc

    if not math.isfinite(result):
        raise ValueError(f"{field_name} must be finite")

    return result


def _int_value(
    value: object,
    *,
    field_name: str,
    default: int | None = None,
) -> int:
    if value is None:
        if default is None:
            raise ValueError(f"{field_name} must be an integer")

        return _int_value(
            default,
            field_name=field_name,
        )

    if isinstance(value, bool) or not isinstance(
        value,
        int | float | str,
    ):
        raise TypeError(f"{field_name} must be an integer")

    if isinstance(value, float) and (
        not math.isfinite(value) or not value.is_integer()
    ):
        raise ValueError(f"{field_name} must be an integer")

    if isinstance(value, str):
        normalized = value.strip()

        if not normalized:
            raise ValueError(f"{field_name} must be an integer")

        try:
            numeric = float(normalized)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an integer") from exc

        if not math.isfinite(numeric) or not numeric.is_integer():
            raise ValueError(f"{field_name} must be an integer")

        return int(numeric)

    return int(value)


def _three_values(
    value: object,
    *,
    field_name: str,
) -> tuple[float, float, float] | None:
    if value is None:
        return None

    if (
        not isinstance(value, Sequence)
        or isinstance(
            value,
            (
                str,
                bytes,
                bytearray,
            ),
        )
        or len(value) != 3
    ):
        raise ValueError(f"{field_name} must contain exactly 3 values")

    values: list[float] = []

    for item in value:
        values.append(
            _float_value(
                item,
                field_name=f"{field_name} value",
            )
        )

    return (
        values[0],
        values[1],
        values[2],
    )


def _mapping_value(
    value: object,
    *,
    field_name: str,
) -> Mapping[str, object] | None:
    if value is None:
        return None

    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError(f"{field_name} must be an object")

    mapping = cast(
        Mapping[object, object],
        value,
    )

    if not all(isinstance(key, str) for key in mapping):
        raise TypeError(f"{field_name} keys must be strings")

    return cast(
        Mapping[str, object],
        mapping,
    )


@dataclass(
    frozen=True,
    slots=True,
)
class SteeringCalibration:
    offset: float = 0.0

    def __post_init__(self) -> None:
        offset = _float_value(
            self.offset,
            field_name="steering offset",
        )

        if not -30.0 <= offset <= 30.0:
            raise ValueError("steering offset must be between -30 and 30 degrees")

        object.__setattr__(
            self,
            "offset",
            offset,
        )

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object] | None,
    ) -> SteeringCalibration:
        mapping = _mapping_value(
            value,
            field_name="steering calibration",
        )

        if mapping is None:
            return cls()

        return cls(
            offset=_float_value(
                mapping.get("offset"),
                field_name="steering offset",
                default=0.0,
            )
        )

    @property
    def adjusted(self) -> bool:
        return self.offset != 0.0


@dataclass(frozen=True, slots=True)
class MotorCalibration:
    left_trim: float = 1.0
    right_trim: float = 1.0

    def __post_init__(self) -> None:
        left_trim = _float_value(
            self.left_trim,
            field_name="left_trim",
        )

        right_trim = _float_value(
            self.right_trim,
            field_name="right_trim",
        )

        for name, trim in (
            (
                "left_trim",
                left_trim,
            ),
            (
                "right_trim",
                right_trim,
            ),
        ):
            if not 0.0 <= trim <= 1.0:
                raise ValueError(f"{name} must be between 0.0 and 1.0")

        object.__setattr__(
            self,
            "left_trim",
            left_trim,
        )

        object.__setattr__(
            self,
            "right_trim",
            right_trim,
        )

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object] | None,
    ) -> MotorCalibration:
        mapping = _mapping_value(
            value,
            field_name="motor calibration",
        )

        if mapping is None:
            return cls()

        return cls(
            left_trim=_float_value(
                mapping.get("left_trim"),
                field_name="left motor trim",
                default=1.0,
            ),
            right_trim=_float_value(
                mapping.get("right_trim"),
                field_name="right motor trim",
                default=1.0,
            ),
        )

    @property
    def adjusted(self) -> bool:
        return self.left_trim != 1.0 or self.right_trim != 1.0


@dataclass(frozen=True, slots=True)
class CameraMountCalibration:
    pan_offset: float = 0.0
    tilt_offset: float = 0.0

    def __post_init__(self) -> None:
        pan_offset = _float_value(
            self.pan_offset,
            field_name="pan_offset",
        )

        tilt_offset = _float_value(
            self.tilt_offset,
            field_name="tilt_offset",
        )

        for name, offset in (
            (
                "pan_offset",
                pan_offset,
            ),
            (
                "tilt_offset",
                tilt_offset,
            ),
        ):
            if not -30.0 <= offset <= 30.0:
                raise ValueError(f"{name} must be between -30 and 30 degrees")

        object.__setattr__(
            self,
            "pan_offset",
            pan_offset,
        )

        object.__setattr__(
            self,
            "tilt_offset",
            tilt_offset,
        )

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object] | None,
    ) -> CameraMountCalibration:
        mapping = _mapping_value(
            value,
            field_name="camera mount calibration",
        )

        if mapping is None:
            return cls()

        return cls(
            pan_offset=_float_value(
                mapping.get("pan_offset"),
                field_name="camera pan offset",
                default=0.0,
            ),
            tilt_offset=_float_value(
                mapping.get("tilt_offset"),
                field_name="camera tilt offset",
                default=0.0,
            ),
        )

    @property
    def adjusted(self) -> bool:
        return self.pan_offset != 0.0 or self.tilt_offset != 0.0


@dataclass(frozen=True, slots=True)
class GrayscaleCalibration:
    floor: (
        tuple[
            float,
            float,
            float,
        ]
        | None
    ) = None

    line: (
        tuple[
            float,
            float,
            float,
        ]
        | None
    ) = None

    def __post_init__(self) -> None:
        floor = _three_values(
            self.floor,
            field_name="grayscale floor",
        )

        line = _three_values(
            self.line,
            field_name="grayscale line",
        )

        if floor is None and line is not None:
            raise ValueError(
                "grayscale floor and line must both be set or both be empty"
            )

        if floor is not None and line is None:
            raise ValueError(
                "grayscale floor and line must both be set or both be empty"
            )

        object.__setattr__(
            self,
            "floor",
            floor,
        )

        object.__setattr__(
            self,
            "line",
            line,
        )

    @property
    def calibrated(self) -> bool:
        return self.floor is not None and self.line is not None

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object] | None,
    ) -> GrayscaleCalibration:
        mapping = _mapping_value(
            value,
            field_name="grayscale calibration",
        )

        if mapping is None:
            return cls()

        return cls(
            floor=_three_values(
                mapping.get("floor"),
                field_name="grayscale floor",
            ),
            line=_three_values(
                mapping.get("line"),
                field_name="grayscale line",
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class RobotCalibration:
    version: int = CALIBRATION_VERSION

    camera_mount: CameraMountCalibration = field(default_factory=CameraMountCalibration)
    steering: SteeringCalibration = field(default_factory=SteeringCalibration)
    motors: MotorCalibration = field(default_factory=MotorCalibration)
    grayscale: GrayscaleCalibration = field(default_factory=GrayscaleCalibration)

    def __post_init__(self) -> None:
        version = _int_value(
            self.version,
            field_name="calibration version",
        )

        if version != CALIBRATION_VERSION:
            raise ValueError(f"unsupported calibration version: {version}")

        object.__setattr__(
            self,
            "version",
            version,
        )

    @classmethod
    def default(
        cls,
    ) -> RobotCalibration:
        return cls()

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> RobotCalibration:
        if not isinstance(
            value,
            Mapping,
        ):
            raise TypeError("calibration data must be an object")

        mapping = cast(
            Mapping[str, object],
            value,
        )

        version = _int_value(
            mapping.get("version"),
            field_name="calibration version",
            default=CALIBRATION_VERSION,
        )

        camera_mount_value = _mapping_value(
            mapping.get("camera_mount"),
            field_name="camera_mount calibration",
        )

        steering_value = _mapping_value(
            mapping.get("steering"),
            field_name="steering calibration",
        )

        motors_value = _mapping_value(
            mapping.get("motors"),
            field_name="motors calibration",
        )

        grayscale_value = _mapping_value(
            mapping.get("grayscale"),
            field_name="grayscale calibration",
        )

        return cls(
            version=version,
            camera_mount=CameraMountCalibration.from_dict(camera_mount_value),
            steering=SteeringCalibration.from_dict(steering_value),
            motors=MotorCalibration.from_dict(motors_value),
            grayscale=GrayscaleCalibration.from_dict(grayscale_value),
        )

    def to_dict(
        self,
    ) -> RobotCalibrationDict:
        return {
            "version": self.version,
            "camera_mount": {
                "pan_offset": self.camera_mount.pan_offset,
                "tilt_offset": self.camera_mount.tilt_offset,
            },
            "steering": {
                "offset": self.steering.offset,
            },
            "motors": {
                "left_trim": self.motors.left_trim,
                "right_trim": self.motors.right_trim,
            },
            "grayscale": {
                "floor": self.grayscale.floor,
                "line": self.grayscale.line,
            },
        }
