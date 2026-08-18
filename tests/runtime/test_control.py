from __future__ import annotations

import threading
import unittest
from typing import final
from unittest.mock import patch

from betabox_robotics.runtime.control import (
    RobotRuntimeControl,
)
from betabox_robotics.runtime.errors import RobotRuntimeError


@final
class FakeRuntimeControlClient:
    token: str

    acquire_calls: list[str]
    renew_calls: list[str]
    release_calls: list[str]

    drive_forward_calls: list[tuple[str, float]]
    drive_backward_calls: list[tuple[str, float]]
    drive_stop_calls: list[str]

    steering_left_calls: list[tuple[str, float]]
    steering_right_calls: list[tuple[str, float]]
    steering_center_calls: list[str]
    steering_angle_calls: list[tuple[str, float]]

    camera_pan_calls: list[tuple[str, float, bool]]
    camera_tilt_calls: list[tuple[str, float, bool]]
    camera_center_calls: list[tuple[str, bool]]

    renew_event: threading.Event

    renew_error: RobotRuntimeError | None
    release_error: RobotRuntimeError | None

    def __init__(
        self,
        *,
        token: str = "test-token",
    ) -> None:
        self.token = token

        self.acquire_calls = []
        self.renew_calls = []
        self.release_calls = []

        self.drive_forward_calls = []
        self.drive_backward_calls = []
        self.drive_stop_calls = []

        self.steering_left_calls = []
        self.steering_right_calls = []
        self.steering_center_calls = []
        self.steering_angle_calls = []

        self.camera_pan_calls = []
        self.camera_tilt_calls = []
        self.camera_center_calls = []

        self.renew_event = threading.Event()

        self.renew_error = None
        self.release_error = None

    def acquire_control(
        self,
        owner: str,
    ) -> str:
        self.acquire_calls.append(owner)

        return self.token

    def renew_control(
        self,
        token: str,
    ) -> None:
        self.renew_calls.append(token)
        self.renew_event.set()

        error = self.renew_error

        if error is not None:
            raise error

    def release_control(
        self,
        token: str,
    ) -> None:
        self.release_calls.append(token)

        error = self.release_error

        if error is not None:
            raise error

    def drive_forward(
        self,
        token: str,
        speed: float = 20,
    ) -> None:
        self.drive_forward_calls.append(
            (
                token,
                speed,
            )
        )

    def drive_backward(
        self,
        token: str,
        speed: float = 20,
    ) -> None:
        self.drive_backward_calls.append(
            (
                token,
                speed,
            )
        )

    def drive_stop(
        self,
        token: str,
    ) -> None:
        self.drive_stop_calls.append(token)

    def steering_left(
        self,
        token: str,
        angle: float = 30,
    ) -> None:
        self.steering_left_calls.append(
            (
                token,
                angle,
            )
        )

    def steering_right(
        self,
        token: str,
        angle: float = 30,
    ) -> None:
        self.steering_right_calls.append(
            (
                token,
                angle,
            )
        )

    def steering_center(
        self,
        token: str,
    ) -> None:
        self.steering_center_calls.append(token)

    def steering_angle(
        self,
        token: str,
        angle: float,
    ) -> None:
        self.steering_angle_calls.append(
            (
                token,
                angle,
            )
        )

    def camera_pan(
        self,
        token: str,
        angle: float,
        *,
        smooth: bool = True,
    ) -> None:
        self.camera_pan_calls.append(
            (
                token,
                angle,
                smooth,
            )
        )

    def camera_tilt(
        self,
        token: str,
        angle: float,
        *,
        smooth: bool = True,
    ) -> None:
        self.camera_tilt_calls.append(
            (
                token,
                angle,
                smooth,
            )
        )

    def camera_center(
        self,
        token: str,
        *,
        smooth: bool = True,
    ) -> None:
        self.camera_center_calls.append(
            (
                token,
                smooth,
            )
        )


def _control(
    *,
    owner: str = "Test Client",
) -> tuple[
    FakeRuntimeControlClient,
    RobotRuntimeControl,
]:
    client = FakeRuntimeControlClient()

    control = RobotRuntimeControl(
        client,
        owner,
    )

    return (
        client,
        control,
    )


@final
class RobotRuntimeControlInitTests(unittest.TestCase):
    def test_initial_state(self) -> None:
        client, control = _control()

        self.assertIs(
            control.client,
            client,
        )
        self.assertEqual(
            control.owner,
            "Test Client",
        )
        self.assertFalse(control.closed)
        self.assertFalse(control.active)

    def test_owner_is_trimmed(self) -> None:
        client = FakeRuntimeControlClient()

        control = RobotRuntimeControl(
            client,
            "  Test Client  ",
        )

        self.assertEqual(
            control.owner,
            "Test Client",
        )

    def test_rejects_empty_owner(self) -> None:
        client = FakeRuntimeControlClient()

        with self.assertRaisesRegex(
            ValueError,
            "owner cannot be empty",
        ):
            _ = RobotRuntimeControl(
                client,
                "   ",
            )

    def test_token_before_start_raises(self) -> None:
        _, control = _control()

        with self.assertRaisesRegex(
            RuntimeError,
            "runtime control has not been acquired",
        ):
            _ = control.token


@final
class RobotRuntimeControlLifecycleTests(unittest.TestCase):
    def test_start_acquires_control(self) -> None:
        client, control = _control()

        try:
            control.start()

            self.assertEqual(
                client.acquire_calls,
                ["Test Client"],
            )
            self.assertEqual(
                control.token,
                "test-token",
            )
            self.assertTrue(control.active)

        finally:
            control.close()

    def test_start_is_idempotent(self) -> None:
        client, control = _control()

        try:
            control.start()
            control.start()

            self.assertEqual(
                client.acquire_calls,
                ["Test Client"],
            )

        finally:
            control.close()

    def test_start_after_close_raises(self) -> None:
        _, control = _control()

        control.close()

        with self.assertRaisesRegex(
            RuntimeError,
            "runtime control session is closed",
        ):
            control.start()

    def test_close_releases_control(self) -> None:
        client, control = _control()

        control.start()
        control.close()

        self.assertEqual(
            client.release_calls,
            ["test-token"],
        )
        self.assertTrue(control.closed)
        self.assertFalse(control.active)

    def test_close_without_start_does_not_release(
        self,
    ) -> None:
        client, control = _control()

        control.close()

        self.assertEqual(
            client.release_calls,
            [],
        )
        self.assertTrue(control.closed)

    def test_close_is_idempotent(self) -> None:
        client, control = _control()

        control.start()

        control.close()
        control.close()

        self.assertEqual(
            client.release_calls,
            ["test-token"],
        )

    def test_close_ignores_release_error(
        self,
    ) -> None:
        client, control = _control()

        client.release_error = RobotRuntimeError("release failed")

        control.start()

        control.close()

        self.assertTrue(control.closed)
        self.assertFalse(control.active)
        self.assertEqual(
            client.release_calls,
            ["test-token"],
        )

    def test_context_manager_acquires_and_releases(
        self,
    ) -> None:
        client, control = _control()

        with control as entered:
            self.assertIs(
                entered,
                control,
            )
            self.assertTrue(control.active)

        self.assertTrue(control.closed)
        self.assertFalse(control.active)

        self.assertEqual(
            client.acquire_calls,
            ["Test Client"],
        )
        self.assertEqual(
            client.release_calls,
            ["test-token"],
        )


@final
class RobotRuntimeControlRenewalTests(unittest.TestCase):
    def test_control_renews_lease(self) -> None:
        client, control = _control()

        with patch(
            "betabox_robotics.runtime.control.CONTROL_RENEW_INTERVAL",
            0.01,
        ):
            try:
                control.start()

                renewed = client.renew_event.wait(
                    timeout=1.0,
                )

                self.assertTrue(
                    renewed,
                    "control lease was not renewed",
                )

                self.assertGreaterEqual(
                    len(client.renew_calls),
                    1,
                )

                self.assertEqual(
                    client.renew_calls[0],
                    "test-token",
                )

            finally:
                control.close()

    def test_renew_error_stops_renewal_loop(
        self,
    ) -> None:
        client, control = _control()

        client.renew_error = RobotRuntimeError("lease lost")

        with patch(
            "betabox_robotics.runtime.control.CONTROL_RENEW_INTERVAL",
            0.01,
        ):
            try:
                control.start()

                renewed = client.renew_event.wait(
                    timeout=1.0,
                )

                self.assertTrue(
                    renewed,
                    "renewal attempt did not occur",
                )

            finally:
                control.close()

        self.assertEqual(
            client.renew_calls,
            ["test-token"],
        )


@final
class RobotRuntimeControlDriveTests(unittest.TestCase):
    def test_forward(self) -> None:
        client, control = _control()

        try:
            control.start()
            control.forward(25)

            self.assertEqual(
                client.drive_forward_calls,
                [
                    (
                        "test-token",
                        25,
                    )
                ],
            )

        finally:
            control.close()

    def test_backward(self) -> None:
        client, control = _control()

        try:
            control.start()
            control.backward(30)

            self.assertEqual(
                client.drive_backward_calls,
                [
                    (
                        "test-token",
                        30,
                    )
                ],
            )

        finally:
            control.close()

    def test_stop(self) -> None:
        client, control = _control()

        try:
            control.start()
            control.stop()

            self.assertEqual(
                client.drive_stop_calls,
                ["test-token"],
            )

        finally:
            control.close()

    def test_left(self) -> None:
        client, control = _control()

        try:
            control.start()
            control.left(15)

            self.assertEqual(
                client.steering_left_calls,
                [
                    (
                        "test-token",
                        15,
                    )
                ],
            )

        finally:
            control.close()

    def test_right(self) -> None:
        client, control = _control()

        try:
            control.start()
            control.right(20)

            self.assertEqual(
                client.steering_right_calls,
                [
                    (
                        "test-token",
                        20,
                    )
                ],
            )

        finally:
            control.close()

    def test_center(self) -> None:
        client, control = _control()

        try:
            control.start()
            control.center()

            self.assertEqual(
                client.steering_center_calls,
                ["test-token"],
            )

        finally:
            control.close()

    def test_steering_angle(self) -> None:
        client, control = _control()

        try:
            control.start()
            control.steering_angle(-12.5)

            self.assertEqual(
                client.steering_angle_calls,
                [
                    (
                        "test-token",
                        -12.5,
                    )
                ],
            )

        finally:
            control.close()

    def test_drive_command_before_start_raises(
        self,
    ) -> None:
        _, control = _control()

        with self.assertRaisesRegex(
            RuntimeError,
            "runtime control has not been acquired",
        ):
            control.forward(20)


@final
class RobotRuntimeControlCameraTests(unittest.TestCase):
    def test_camera_pan(self) -> None:
        client, control = _control()

        try:
            control.start()

            control.camera_pan(
                15,
                smooth=False,
            )

            self.assertEqual(
                client.camera_pan_calls,
                [
                    (
                        "test-token",
                        15,
                        False,
                    )
                ],
            )

        finally:
            control.close()

    def test_camera_tilt(self) -> None:
        client, control = _control()

        try:
            control.start()

            control.camera_tilt(
                -10,
            )

            self.assertEqual(
                client.camera_tilt_calls,
                [
                    (
                        "test-token",
                        -10,
                        True,
                    )
                ],
            )

        finally:
            control.close()

    def test_camera_center(self) -> None:
        client, control = _control()

        try:
            control.start()

            control.camera_center(
                smooth=False,
            )

            self.assertEqual(
                client.camera_center_calls,
                [
                    (
                        "test-token",
                        False,
                    )
                ],
            )

        finally:
            control.close()


if __name__ == "__main__":
    _ = unittest.main()
