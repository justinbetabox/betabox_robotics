#!/usr/bin/env python3

from unittest.mock import patch

from betabox_robotics.camera import (
    CameraMount,
    CameraMountError,
)
from betabox_robotics.hardware import Pins
from betabox_robotics.robots.config import (
    CameraMountConfig,
)


class FakeServo:
    instances: list["FakeServo"] = []

    def __init__(
        self,
        channel,
        *,
        min_angle: float = -90,
        max_angle: float = 90,
        **kwargs,
    ) -> None:
        self.channel = channel
        self.min_angle = float(min_angle)
        self.max_angle = float(max_angle)
        self.moves: list[tuple[float, bool]] = []
        self.closed = False

        FakeServo.instances.append(self)

    def move_to(
        self,
        angle: float,
        *,
        smooth: bool = True,
    ) -> None:
        self.moves.append(
            (
                float(angle),
                smooth,
            )
        )

    def close(self) -> None:
        self.closed = True


def make_config(
    *,
    pan_reversed: bool = False,
    tilt_reversed: bool = False,
) -> CameraMountConfig:
    return CameraMountConfig(
        pan_servo=Pins.P0,
        tilt_servo=Pins.P1,
        pan_min_angle=-45.0,
        pan_max_angle=45.0,
        tilt_min_angle=-30.0,
        tilt_max_angle=45.0,
        pan_center=0.0,
        tilt_center=5.0,
        pan_reversed=pan_reversed,
        tilt_reversed=tilt_reversed,
    )


def make_mount(
    *,
    pan_reversed: bool = False,
    tilt_reversed: bool = False,
) -> tuple[
    CameraMount,
    FakeServo,
    FakeServo,
]:
    FakeServo.instances.clear()

    config = make_config(
        pan_reversed=pan_reversed,
        tilt_reversed=tilt_reversed,
    )

    mount = CameraMount(config)

    assert len(FakeServo.instances) == 2

    pan_servo = FakeServo.instances[0]
    tilt_servo = FakeServo.instances[1]

    return mount, pan_servo, tilt_servo


@patch(
    "betabox_robotics.camera.mount.Servo",
    FakeServo,
)
def test_camera_mount_constructs_servos():
    mount, pan_servo, tilt_servo = make_mount()

    assert pan_servo.channel == Pins.P0
    assert tilt_servo.channel == Pins.P1

    assert pan_servo.min_angle == -45.0
    assert pan_servo.max_angle == 45.0

    assert tilt_servo.min_angle == -30.0
    assert tilt_servo.max_angle == 45.0

    mount.close()


@patch(
    "betabox_robotics.camera.mount.Servo",
    FakeServo,
)
def test_look_moves_both_axes():
    mount, pan_servo, tilt_servo = make_mount()

    mount.look(
        pan=20,
        tilt=-10,
        smooth=False,
    )

    assert pan_servo.moves[-1] == (
        20.0,
        False,
    )

    assert tilt_servo.moves[-1] == (
        -10.0,
        False,
    )

    status = mount.status()

    assert status.pan == 20.0
    assert status.tilt == -10.0

    mount.close()


@patch(
    "betabox_robotics.camera.mount.Servo",
    FakeServo,
)
def test_pan_preserves_tilt_state():
    mount, _, tilt_servo = make_mount()

    mount.tilt(15)
    tilt_move_count = len(
        tilt_servo.moves
    )

    mount.pan(25)

    assert mount.status().pan == 25.0
    assert mount.status().tilt == 15.0

    assert len(
        tilt_servo.moves
    ) == tilt_move_count

    mount.close()


@patch(
    "betabox_robotics.camera.mount.Servo",
    FakeServo,
)
def test_tilt_preserves_pan_state():
    mount, pan_servo, _ = make_mount()

    mount.pan(-20)
    pan_move_count = len(
        pan_servo.moves
    )

    mount.tilt(25)

    assert mount.status().pan == -20.0
    assert mount.status().tilt == 25.0

    assert len(
        pan_servo.moves
    ) == pan_move_count

    mount.close()


@patch(
    "betabox_robotics.camera.mount.Servo",
    FakeServo,
)
def test_camera_mount_clamps_angles():
    mount, pan_servo, tilt_servo = make_mount()

    mount.pan(100)
    mount.tilt(-100)

    assert pan_servo.moves[-1][0] == 45.0
    assert tilt_servo.moves[-1][0] == -30.0

    status = mount.status()

    assert status.pan == 45.0
    assert status.tilt == -30.0

    mount.close()


@patch(
    "betabox_robotics.camera.mount.Servo",
    FakeServo,
)
def test_camera_mount_centers_to_configured_values():
    mount, pan_servo, tilt_servo = make_mount()

    mount.look(
        pan=20,
        tilt=-10,
    )

    mount.center(
        smooth=False,
    )

    assert pan_servo.moves[-1] == (
        0.0,
        False,
    )

    assert tilt_servo.moves[-1] == (
        5.0,
        False,
    )

    status = mount.status()

    assert status.pan == 0.0
    assert status.tilt == 5.0

    mount.close()


@patch(
    "betabox_robotics.camera.mount.Servo",
    FakeServo,
)
def test_pan_reversed_inverts_hardware_angle():
    mount, pan_servo, _ = make_mount(
        pan_reversed=True,
    )

    mount.pan(30)

    assert pan_servo.moves[-1][0] == -30.0
    assert mount.status().pan == 30.0

    mount.close()


@patch(
    "betabox_robotics.camera.mount.Servo",
    FakeServo,
)
def test_tilt_reversed_inverts_hardware_angle():
    mount, _, tilt_servo = make_mount(
        tilt_reversed=True,
    )

    mount.tilt(20)

    assert tilt_servo.moves[-1][0] == -20.0
    assert mount.status().tilt == 20.0

    mount.close()


@patch(
    "betabox_robotics.camera.mount.Servo",
    FakeServo,
)
def test_camera_mount_close_closes_both_servos():
    mount, pan_servo, tilt_servo = make_mount()

    mount.close()

    assert mount.closed is True
    assert pan_servo.closed is True
    assert tilt_servo.closed is True


@patch(
    "betabox_robotics.camera.mount.Servo",
    FakeServo,
)
def test_closed_camera_mount_rejects_commands():
    mount, _, _ = make_mount()

    mount.close()

    try:
        mount.pan(10)
        raise AssertionError(
            "expected CameraMountError"
        )
    except CameraMountError:
        pass


if __name__ == "__main__":
    test_camera_mount_constructs_servos()
    test_look_moves_both_axes()
    test_pan_preserves_tilt_state()
    test_tilt_preserves_pan_state()
    test_camera_mount_clamps_angles()
    test_camera_mount_centers_to_configured_values()
    test_pan_reversed_inverts_hardware_angle()
    test_tilt_reversed_inverts_hardware_angle()
    test_camera_mount_close_closes_both_servos()
    test_closed_camera_mount_rejects_commands()

    print()
    print("Camera mount tests complete.")
