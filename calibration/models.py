from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


CALIBRATION_VERSION = 1


def _float_value(
    value: object,
    *,
    field_name: str,
    default: float,
) -> float:
    if value is None:
        return float(default)

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be a number"
        )

    if not isinstance(
        value,
        (
            int,
            float,
            str,
        ),
    ):
        raise ValueError(
            f"{field_name} must be a number"
        )

    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be a number"
        ) from exc

def _int_value(
    value: object,
    *,
    field_name: str,
    default: int,
) -> int:
    if value is None:
        return int(default)

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be an integer"
        )

    if not isinstance(
        value,
        (
            int,
            float,
            str,
        ),
    ):
        raise ValueError(
            f"{field_name} must be an integer"
        )

    try:
        converted = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} must be an integer"
        ) from exc

    if isinstance(value, float) and not value.is_integer():
        raise ValueError(
            f"{field_name} must be an integer"
        )

    return converted

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
        raise ValueError(
            f"{field_name} must contain exactly 3 values"
        )

    try:
        values = tuple(
            float(item)
            for item in value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            f"{field_name} values must be numbers"
        ) from exc

    return (
        values[0],
        values[1],
        values[2],
    )


@dataclass(frozen=True)
class SteeringCalibration:
    offset: float = 0.0

    def __post_init__(self) -> None:
        offset = float(self.offset)

        if not -30.0 <= offset <= 30.0:
            raise ValueError(
                "steering offset must be between "
                "-30 and 30 degrees"
            )

        object.__setattr__(
            self,
            "offset",
            offset,
        )

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object] | None,
    ) -> "SteeringCalibration":
        if value is None:
            return cls()

        return cls(
            offset=_float_value(
                value.get("offset"),
                field_name="steering offset",
                default=0.0,
            )
        )

    @property
    def adjusted(self) -> bool:
        return self.offset != 0.0


@dataclass(frozen=True)
class MotorCalibration:
    left_trim: float = 1.0
    right_trim: float = 1.0

    def __post_init__(self) -> None:
        left_trim = float(
            self.left_trim
        )

        right_trim = float(
            self.right_trim
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
                raise ValueError(
                    f"{name} must be between 0.0 and 1.0"
                )

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
    ) -> "MotorCalibration":
        if value is None:
            return cls()

        return cls(
            left_trim=_float_value(
                value.get("left_trim"),
                field_name="left motor trim",
                default=1.0,
            ),
            right_trim=_float_value(
                value.get("right_trim"),
                field_name="right motor trim",
                default=1.0,
            ),
        )

    @property
    def adjusted(self) -> bool:
        return (
            self.left_trim != 1.0
            or self.right_trim != 1.0
        )

@dataclass(frozen=True)
class CameraMountCalibration:
    pan_offset: float = 0.0
    tilt_offset: float = 0.0

    def __post_init__(self) -> None:
        pan_offset = float(
            self.pan_offset
        )

        tilt_offset = float(
            self.tilt_offset
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
                raise ValueError(
                    f"{name} must be between "
                    "-30 and 30 degrees"
                )

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
    ) -> "CameraMountCalibration":
        if value is None:
            return cls()

        return cls(
            pan_offset=_float_value(
                value.get("pan_offset"),
                field_name="camera pan offset",
                default=0.0,
            ),
            tilt_offset=_float_value(
                value.get("tilt_offset"),
                field_name="camera tilt offset",
                default=0.0
            ),
        )

    @property
    def adjusted(self) -> bool:
        return (
            self.pan_offset != 0.0
            or self.tilt_offset != 0.0
        )

@dataclass(frozen=True)
class GrayscaleCalibration:
    floor: tuple[
        float,
        float,
        float,
    ] | None = None

    line: tuple[
        float,
        float,
        float,
    ] | None = None

    def __post_init__(self) -> None:
        floor = _three_values(
            self.floor,
            field_name="grayscale floor",
        )

        line = _three_values(
            self.line,
            field_name="grayscale line",
        )

        if (
            floor is None
            and line is not None
        ):
            raise ValueError(
                "grayscale floor and line must "
                "both be set or both be empty"
            )

        if (
            floor is not None
            and line is None
        ):
            raise ValueError(
                "grayscale floor and line must "
                "both be set or both be empty"
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
        return (
            self.floor is not None
            and self.line is not None
        )

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object] | None,
    ) -> "GrayscaleCalibration":
        if value is None:
            return cls()

        return cls(
            floor=_three_values(
                value.get("floor"),
                field_name="grayscale floor",
            ),
            line=_three_values(
                value.get("line"),
                field_name="grayscale line",
            ),
        )

@dataclass(frozen=True)
class RobotCalibration:
    version: int = CALIBRATION_VERSION

    camera_mount: CameraMountCalibration = (
        CameraMountCalibration()
    )

    steering: SteeringCalibration = (
        SteeringCalibration()
    )

    motors: MotorCalibration = (
        MotorCalibration()
    )

    grayscale: GrayscaleCalibration = (
        GrayscaleCalibration()
    )

    def __post_init__(self) -> None:
        version = int(self.version)

        if version != CALIBRATION_VERSION:
            raise ValueError(
                "unsupported calibration version: "
                f"{version}"
            )

        object.__setattr__(
            self,
            "version",
            version,
        )

    @classmethod
    def default(
        cls,
    ) -> "RobotCalibration":
        return cls()

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object],
    ) -> "RobotCalibration":
        if not isinstance(
            value,
            Mapping,
        ):
            raise ValueError(
                "calibration data must be an object"
            )

        version = _int_value(
            value.get("version"),
            field_name="calibration version",
            default=CALIBRATION_VERSION,
        )

        camera_mount_value = value.get(
            "camera_mount"
        )

        if (
            camera_mount_value is not None
            and not isinstance(
                camera_mount_value,
                Mapping,
            )
        ):
            raise ValueError(
                "camera_mount calibration must be an object"
            )

        steering_value = value.get(
            "steering"
        )

        if (
            steering_value is not None
            and not isinstance(
                steering_value,
                Mapping,
            )
        ):
            raise ValueError(
                "steering calibration must be an object"
            )

        motors_value = value.get(
            "motors"
        )

        if (
            motors_value is not None
            and not isinstance(
                motors_value,
                Mapping,
            )
        ):
            raise ValueError(
                "motors calibration must be an object"
            )

        grayscale_value = value.get(
            "grayscale"
        )

        if (
            grayscale_value is not None
            and not isinstance(
                grayscale_value,
                Mapping,
            )
        ):
            raise ValueError(
                "grayscale calibration must be an object"
            )

        return cls(
            version=version,
            camera_mount=(
                CameraMountCalibration.from_dict(
                    camera_mount_value
                )
            ),
            steering=SteeringCalibration.from_dict(
                steering_value
            ),
            motors=MotorCalibration.from_dict(
                motors_value
            ),
            grayscale=GrayscaleCalibration.from_dict(
                grayscale_value
            ),
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(self)
