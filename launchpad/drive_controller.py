from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from math import isfinite
from typing import TYPE_CHECKING

from betabox_robotics.calibration import (
    CalibrationManager,
)
from betabox_robotics.exceptions import BetaboxError

if TYPE_CHECKING:
    from betabox_robotics import BetaboxCar


def _validate_axis(
    value: object,
    *,
    name: str,
) -> float:
    result = _validate_number(
        value,
        name=name,
    )

    if not -1.0 <= result <= 1.0:
        raise ValueError(f"{name} must be between -1.0 and 1.0")

    return result


def _validate_flag(
    value: object,
    *,
    name: str,
) -> bool:
    if not isinstance(
        value,
        bool,
    ):
        raise TypeError(f"{name} must be a boolean")

    return value


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

    if not isfinite(result):
        raise ValueError(f"{name} must be finite")

    return result


def _validate_generation(
    value: object,
) -> int:
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError("generation must be an integer")

    if value < 0:
        raise ValueError("generation cannot be negative")

    return value


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
        raise ValueError(f"{name} must be greater than 0")

    return result


def _validate_maximum_speed(
    value: object,
) -> int:
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError("maximum_speed must be an integer")

    if not 1 <= value <= 100:
        raise ValueError("maximum_speed must be between 1 and 100")

    return value


@dataclass(
    frozen=True,
    slots=True,
)
class ControlState:
    """
    Complete desired state for browser-based robot control.

    Normalized axis values range from -1.0 to 1.0.

    throttle:
        1.0 = full forward
        0.0 = stopped
       -1.0 = full reverse

    steering:
       -1.0 = full left
        0.0 = centered
        1.0 = full right

    Camera and accessory fields are included now so the protocol can
    grow without another structural rewrite.
    """

    throttle: float = 0.0
    steering: float = 0.0

    camera_pan: float = 0.0
    camera_tilt: float = 0.0

    headlights: bool = False
    horn: bool = False

    def __post_init__(
        self,
    ) -> None:
        for name in (
            "throttle",
            "steering",
            "camera_pan",
            "camera_tilt",
        ):
            object.__setattr__(
                self,
                name,
                _validate_axis(
                    getattr(
                        self,
                        name,
                    ),
                    name=name,
                ),
            )

        object.__setattr__(
            self,
            "headlights",
            _validate_flag(
                self.headlights,
                name="headlights",
            ),
        )
        object.__setattr__(
            self,
            "horn",
            _validate_flag(
                self.horn,
                name="horn",
            ),
        )


def _validate_client_id(
    value: object,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError("client_id must be a string")

    result = value.strip()

    if not result:
        raise ValueError("client_id cannot be empty")

    return result


def _validate_state(
    value: object,
) -> ControlState:
    if not isinstance(
        value,
        ControlState,
    ):
        raise TypeError("state must be a ControlState")

    return value


class DriveControlError(RuntimeError):
    """Raised when a manual-drive command cannot be completed."""


class ManualDriveController:
    """
    Owns manual browser control of the robot.

    Only one browser client may control the robot at a time. The robot
    automatically stops when the controller disconnects or stops sending
    heartbeats.
    """

    def __init__(
        self,
        calibration_manager: CalibrationManager,
        *,
        heartbeat_timeout: float = 1.0,
        update_hz: float = 20.0,
        maximum_speed: int = 100,
        steering_angle: float = 30.0,
    ) -> None:
        if not isinstance(
            calibration_manager,
            CalibrationManager,
        ):
            raise TypeError("calibration_manager must be a CalibrationManager")

        self.calibration_manager = calibration_manager

        self.heartbeat_timeout = _validate_positive_number(
            heartbeat_timeout,
            name="heartbeat_timeout",
        )
        self.update_hz = _validate_positive_number(
            update_hz,
            name="update_hz",
        )
        self.maximum_speed = _validate_maximum_speed(maximum_speed)
        self.steering_angle = _validate_positive_number(
            steering_angle,
            name="steering_angle",
        )

        self.update_interval = 1.0 / self.update_hz

        self._desired_state = ControlState()
        self._last_applied_state: ControlState | None = None
        self._state_generation = 0

        self._robot: BetaboxCar | None = None
        self._owner: str | None = None
        self._claiming: str | None = None
        self._last_heartbeat = 0.0

        self._lock = asyncio.Lock()
        self._hardware_lock = asyncio.Lock()
        self._control_task: asyncio.Task[None] | None = None
        self._watchdog_task: asyncio.Task[None] | None = None
        self._closed = False

    @property
    def owner(self) -> str | None:
        return self._owner

    @property
    def available(self) -> bool:
        return not self._closed and self._owner is None

    async def start(self) -> None:
        self._require_open()

        if self._watchdog_task is None or self._watchdog_task.done():
            self._watchdog_task = asyncio.create_task(
                self._watchdog_loop(),
                name="LaunchpadDriveWatchdog",
            )

        if self._control_task is None or self._control_task.done():
            self._control_task = asyncio.create_task(
                self._control_loop(),
                name="LaunchpadControlState",
            )

    async def close(self) -> None:
        if self._closed:
            return

        self._closed = True

        tasks = [
            task
            for task in (
                self._watchdog_task,
                self._control_task,
            )
            if task is not None
        ]

        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )

        self._watchdog_task = None
        self._control_task = None

        async with self._lock:
            self._owner = None
            self._claiming = None
            self._last_heartbeat = 0.0
            self._desired_state = ControlState()
            self._last_applied_state = None
            self._state_generation += 1

            robot = self._robot
            self._robot = None

        try:
            await self._stop_center_close(robot)
        except DriveControlError:
            pass

    async def owns(
        self,
        client_id: str,
    ) -> bool:
        client_id_value = _validate_client_id(client_id)

        async with self._lock:
            return (
                not self._closed
                and self._owner == client_id_value
                and self._robot is not None
            )

    async def claim(
        self,
        client_id: str,
    ) -> bool:
        client_id_value = _validate_client_id(client_id)

        async with self._lock:
            self._require_open()

            if self._owner is not None or self._claiming is not None:
                return False

            self._claiming = client_id_value

        claim_succeeded = False

        try:
            await self._ensure_robot()
            await self._safe_neutralize()

            async with self._lock:
                self._require_open()

                self._owner = client_id_value
                self._last_heartbeat = time.monotonic()
                self._desired_state = ControlState()
                self._last_applied_state = None
                self._state_generation += 1

                claim_succeeded = True

            return True

        finally:
            robot = None

            async with self._lock:
                if self._claiming == client_id_value:
                    self._claiming = None

                if not claim_succeeded:
                    if self._owner == client_id_value:
                        self._owner = None

                    self._last_heartbeat = 0.0
                    self._desired_state = ControlState()
                    self._last_applied_state = None
                    self._state_generation += 1

                    robot = self._robot
                    self._robot = None

            if robot is not None:
                try:
                    await self._stop_center_close(robot)
                except DriveControlError:
                    pass

    async def release(
        self,
        client_id: str,
    ) -> None:
        client_id_value = _validate_client_id(client_id)

        async with self._lock:
            if self._owner != client_id_value:
                return

            self._owner = None
            self._last_heartbeat = 0.0
            self._desired_state = ControlState()
            self._last_applied_state = None
            self._state_generation += 1

            robot = self._robot
            self._robot = None

        try:
            await self._stop_center_close(robot)
        except DriveControlError:
            pass

    async def heartbeat(
        self,
        client_id: str,
    ) -> None:
        client_id_value = _validate_client_id(client_id)

        async with self._lock:
            self._require_owner(client_id_value)
            self._last_heartbeat = time.monotonic()

    async def update_state(
        self,
        client_id: str,
        state: ControlState,
    ) -> None:
        client_id_value = _validate_client_id(client_id)
        state_value = _validate_state(state)

        async with self._lock:
            self._require_owner(client_id_value)

            self._desired_state = state_value
            self._state_generation += 1
            self._last_heartbeat = time.monotonic()

    async def emergency_stop(
        self,
        client_id: str | None = None,
    ) -> None:
        if client_id is None:
            client_id_value = None
        else:
            client_id_value = _validate_client_id(client_id)

        async with self._lock:
            if client_id_value is not None and self._owner != client_id_value:
                return

            current = self._desired_state

            self._desired_state = ControlState(
                throttle=0.0,
                steering=0.0,
                camera_pan=current.camera_pan,
                camera_tilt=current.camera_tilt,
                headlights=current.headlights,
                horn=False,
            )

            self._last_applied_state = None
            self._state_generation += 1

        await self._safe_neutralize()

    async def _ensure_robot(self) -> None:
        if self._robot is not None:
            return

        robot = await asyncio.to_thread(
            self.calibration_manager.create_car,
            owner="Manual Drive",
        )

        if robot is None:
            raise DriveControlError("failed to create robot")

        self._robot = robot

    async def _stop_center_close(
        self,
        robot: BetaboxCar | None,
    ) -> None:
        if robot is None:
            return

        async with self._hardware_lock:
            try:
                await asyncio.to_thread(robot.close)
            except Exception as exc:
                raise DriveControlError(f"failed to close robot: {exc}") from exc

    async def _safe_neutralize(
        self,
    ) -> None:
        async with self._hardware_lock:
            robot = self._robot

            if robot is None:
                return

            try:
                await asyncio.to_thread(robot.stop)
            except BetaboxError as exc:
                raise DriveControlError(f"failed to stop robot: {exc}") from exc

            try:
                await asyncio.to_thread(robot.center)
            except BetaboxError:
                pass

    async def _control_loop(
        self,
    ) -> None:
        while True:
            started = time.monotonic()

            async with self._lock:
                owner = self._owner
                robot_ready = self._robot is not None
                state = self._desired_state
                generation = self._state_generation
                last_applied = self._last_applied_state

            if owner is not None and robot_ready and state != last_applied:
                try:
                    await self._apply_state(
                        state,
                        generation,
                    )
                except DriveControlError:
                    await self.emergency_stop()

            elapsed = time.monotonic() - started

            delay = max(
                0.0,
                self.update_interval - elapsed,
            )

            await asyncio.sleep(delay)

    async def _watchdog_loop(
        self,
    ) -> None:
        while True:
            await asyncio.sleep(0.1)

            robot = None

            async with self._lock:
                if self._owner is None:
                    continue

                elapsed = time.monotonic() - self._last_heartbeat

                if elapsed <= self.heartbeat_timeout:
                    continue

                self._owner = None
                self._last_heartbeat = 0.0
                self._desired_state = ControlState()
                self._last_applied_state = None
                self._state_generation += 1

                robot = self._robot
                self._robot = None

            try:
                await self._stop_center_close(robot)
            except DriveControlError:
                pass

    async def _apply_state(
        self,
        state: ControlState,
        generation: int,
    ) -> None:
        state_value = _validate_state(state)
        generation_value = _validate_generation(generation)

        async with self._hardware_lock:
            async with self._lock:
                if (
                    self._owner is None
                    or self._robot is None
                    or generation_value != self._state_generation
                ):
                    return

                previous = self._last_applied_state

            steering_changed = (
                previous is None or state_value.steering != previous.steering
            )
            throttle_changed = (
                previous is None or state_value.throttle != previous.throttle
            )
            camera_changed = (
                previous is None
                or state_value.camera_pan != previous.camera_pan
                or state_value.camera_tilt != previous.camera_tilt
            )

            if steering_changed:
                await self._apply_steering_axis(state_value.steering)

            if not await self._generation_is_current(generation_value):
                return

            if throttle_changed:
                await self._apply_throttle(state_value.throttle)

            if not await self._generation_is_current(generation_value):
                return

            if camera_changed:
                await self._apply_camera_axes(
                    state_value.camera_pan,
                    state_value.camera_tilt,
                )

            async with self._lock:
                if (
                    self._owner is not None
                    and generation_value == self._state_generation
                ):
                    self._last_applied_state = state_value

    async def _generation_is_current(
        self,
        generation: int,
    ) -> bool:
        generation_value = _validate_generation(generation)

        async with self._lock:
            return generation_value == self._state_generation

    async def _apply_throttle(
        self,
        throttle: float,
    ) -> None:
        throttle_value = _validate_axis(
            throttle,
            name="throttle",
        )
        robot = self._require_robot()

        speed = round(abs(throttle_value) * self.maximum_speed)

        try:
            if throttle_value > 0:
                await asyncio.to_thread(
                    robot.forward,
                    speed,
                )
                return

            if throttle_value < 0:
                await asyncio.to_thread(
                    robot.backward,
                    speed,
                )
                return

            await self._stop_motion()

        except DriveControlError:
            raise
        except Exception as exc:
            raise DriveControlError(f"failed to apply throttle: {exc}") from exc

    async def _stop_motion(
        self,
    ) -> None:
        """
        Stop motor movement without changing steering.
        """

        robot = self._require_robot()

        try:
            await asyncio.to_thread(robot.stop)
        except Exception as exc:
            raise DriveControlError(f"failed to stop robot motion: {exc}") from exc

    async def _apply_steering_axis(
        self,
        steering: float,
    ) -> None:
        steering_value = _validate_axis(
            steering,
            name="steering",
        )
        robot = self._require_robot()

        angle = steering_value * self.steering_angle

        try:
            if angle < 0:
                await asyncio.to_thread(
                    robot.left,
                    abs(angle),
                )
                return

            if angle > 0:
                await asyncio.to_thread(
                    robot.right,
                    angle,
                )
                return

            await asyncio.to_thread(robot.center)

        except Exception as exc:
            raise DriveControlError(f"failed to apply steering: {exc}") from exc

    async def _apply_camera_axes(
        self,
        pan: float,
        tilt: float,
    ) -> None:
        pan_value = _validate_axis(
            pan,
            name="camera_pan",
        )
        tilt_value = _validate_axis(
            tilt,
            name="camera_tilt",
        )

        robot = self._require_robot()
        config = robot.config.camera_mount

        pan_angle = self._camera_axis_to_angle(
            pan_value,
            minimum=config.pan_min_angle,
            center=config.pan_center,
            maximum=config.pan_max_angle,
        )
        tilt_angle = self._camera_axis_to_angle(
            tilt_value,
            minimum=config.tilt_min_angle,
            center=config.tilt_center,
            maximum=config.tilt_max_angle,
        )

        try:
            await asyncio.to_thread(
                robot.look,
                pan=pan_angle,
                tilt=tilt_angle,
                smooth=False,
            )
        except Exception as exc:
            raise DriveControlError(f"failed to apply camera position: {exc}") from exc

    def _camera_axis_to_angle(
        self,
        value: float,
        *,
        minimum: float,
        center: float,
        maximum: float,
    ) -> float:
        """
        Convert a normalized axis into an asymmetric angle range.
        """

        value_value = _validate_axis(
            value,
            name="camera axis",
        )
        minimum_value = _validate_number(
            minimum,
            name="minimum",
        )
        center_value = _validate_number(
            center,
            name="center",
        )
        maximum_value = _validate_number(
            maximum,
            name="maximum",
        )

        if not (minimum_value <= center_value <= maximum_value):
            raise ValueError("camera angles must satisfy minimum <= center <= maximum")

        if value_value < 0:
            return center_value + (abs(value_value) * (minimum_value - center_value))

        return center_value + (value_value * (maximum_value - center_value))

    def _require_open(self) -> None:
        if self._closed:
            raise DriveControlError("manual drive controller is closed")

    def _require_owner(
        self,
        client_id: str,
    ) -> None:
        client_id_value = _validate_client_id(client_id)

        self._require_open()

        if self._owner != client_id_value:
            raise DriveControlError("manual drive control is not owned by this client")

    def _require_robot(
        self,
    ) -> BetaboxCar:
        robot = self._robot

        if robot is None:
            raise DriveControlError("robot is not started")

        return robot
