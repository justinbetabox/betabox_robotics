from __future__ import annotations

import asyncio
import time

from dataclasses import dataclass
from math import isfinite
from typing import TYPE_CHECKING

from betabox_robotics.calibration import (
    CalibrationManager,
)

if TYPE_CHECKING:
    from betabox_robotics import BetaboxCar


@dataclass(frozen=True)
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

    def __post_init__(self) -> None:
        for name, value in (
            ("throttle", self.throttle),
            ("steering", self.steering),
            ("camera_pan", self.camera_pan),
            ("camera_tilt", self.camera_tilt),
        ):
            if not isfinite(value):
                raise ValueError(
                    f"{name} must be finite"
                )

            if not -1.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between -1.0 and 1.0"
                )


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
            raise TypeError(
                "calibration_manager must be a "
                "CalibrationManager"
            )

        self.calibration_manager = (
            calibration_manager
        )

        if heartbeat_timeout <= 0:
            raise ValueError(
                "heartbeat_timeout must be greater than 0"
            )

        if update_hz <= 0:
            raise ValueError(
                "update_hz must be greater than 0"
            )

        if not 1 <= maximum_speed <= 100:
            raise ValueError(
                "maximum_speed must be between 1 and 100"
            )

        if steering_angle <= 0:
            raise ValueError(
                "steering_angle must be greater than 0"
            )

        self.heartbeat_timeout = float(
            heartbeat_timeout
        )

        self.update_hz = float(
            update_hz
        )

        self.update_interval = (
            1.0 / self.update_hz
        )

        self.maximum_speed = int(
            maximum_speed
        )

        self.steering_angle = float(
            steering_angle
        )

        self._desired_state = ControlState()
        self._last_applied_state: ControlState | None = None
        self._state_generation = 0

        self._robot = None
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
        return (
            not self._closed
            and self._owner is None
        )

    async def owns(
        self,
        client_id: str,
    ) -> bool:
        async with self._lock:
            return (
                not self._closed
                and self._owner == client_id
                and self._robot is not None
            )

    def _camera_axis_to_angle(
        self,
        value: float,
        *,
        minimum: float,
        center: float,
        maximum: float,
    ) -> float:
        """
        Convert a normalized -1.0..1.0 axis into an asymmetric angle range.
        """

        if value < 0:
            return center + (
                abs(value)
                * (minimum - center)
            )

        return center + (
            value
            * (maximum - center)
        )


    async def _apply_camera_axes(
        self,
        pan: float,
        tilt: float,
    ) -> None:
        robot = self._require_robot()
        config = robot.config.camera_mount

        pan_angle = self._camera_axis_to_angle(
            pan,
            minimum=config.pan_min_angle,
            center=config.pan_center,
            maximum=config.pan_max_angle,
        )

        tilt_angle = self._camera_axis_to_angle(
            tilt,
            minimum=config.tilt_min_angle,
            center=config.tilt_center,
            maximum=config.tilt_max_angle,
        )

        await asyncio.to_thread(
            robot.look,
            pan=pan_angle,
            tilt=tilt_angle,
            smooth=False,
        )

    async def start(self) -> None:
        self._require_open()

        if (
            self._watchdog_task is None
            or self._watchdog_task.done()
        ):
            self._watchdog_task = asyncio.create_task(
                self._watchdog_loop(),
                name="LaunchpadDriveWatchdog",
            )

        if (
            self._control_task is None
            or self._control_task.done()
        ):
            self._control_task = asyncio.create_task(
                self._control_loop(),
                name="LaunchpadControlState",
            )


    async def claim(
        self,
        client_id: str,
    ) -> bool:
        async with self._lock:
            self._require_open()

            if (
                self._owner is not None
                or self._claiming is not None
            ):
                return False

            self._claiming = client_id

        claim_succeeded = False

        try:
            await self._ensure_robot()
            await self._safe_neutralize()

            async with self._lock:
                self._require_open()

                self._owner = client_id
                self._last_heartbeat = time.monotonic()
                self._desired_state = ControlState()
                self._last_applied_state = None
                self._state_generation += 1

                claim_succeeded = True

            return True

        finally:
            robot = None

            async with self._lock:
                if self._claiming == client_id:
                    self._claiming = None

                if not claim_succeeded:
                    if self._owner == client_id:
                        self._owner = None

                    self._last_heartbeat = 0.0
                    self._desired_state = ControlState()
                    self._last_applied_state = None
                    self._state_generation += 1

                    robot = self._robot
                    self._robot = None

            if robot is not None:
                await self._stop_center_close(
                    robot
                )

    async def heartbeat(
        self,
        client_id: str,
    ) -> None:
        async with self._lock:
            self._require_owner(client_id)
            self._last_heartbeat = time.monotonic()

    async def update_state(
        self,
        client_id: str,
        state: ControlState,
    ) -> None:
        async with self._lock:
            self._require_owner(client_id)

            self._desired_state = state
            self._state_generation += 1
            self._last_heartbeat = time.monotonic()


    async def emergency_stop(
        self,
        client_id: str | None = None,
    ) -> None:
        async with self._lock:
            if (
                client_id is not None
                and self._owner != client_id
            ):
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

    async def release(
        self,
        client_id: str,
    ) -> None:
        async with self._lock:
            if self._owner != client_id:
                return

            self._owner = None
            self._last_heartbeat = 0.0
            self._desired_state = ControlState()
            self._last_applied_state = None
            self._state_generation += 1

            robot = self._robot
            self._robot = None

        await self._stop_center_close(
            robot
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

        await self._stop_center_close(
            robot
        )

    async def _ensure_robot(self) -> None:
        if self._robot is not None:
            return

        robot = await asyncio.to_thread(
            self.calibration_manager.create_car,
            owner="Manual Drive",
        )

        self._robot = robot


    async def _stop_center_close(
        self,
        robot,
    ) -> None:
        if robot is None:
            return

        async with self._hardware_lock:
            await asyncio.to_thread(
                robot.close
            )

    async def _safe_neutralize(self) -> None:
        async with self._hardware_lock:
            robot = self._robot

            if robot is None:
                return

            try:
                await asyncio.to_thread(
                    robot.stop
                )
            finally:
                try:
                    await asyncio.to_thread(
                        robot.center
                    )
                except Exception:
                    pass

    async def _apply_steering_axis(
        self,
        steering: float,
    ) -> None:
        robot = self._require_robot()

        angle = (
            steering
            * self.steering_angle
        )

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

        await asyncio.to_thread(
            robot.center
        )

    async def _apply_throttle(
        self,
        throttle: float,
    ) -> None:
        robot = self._require_robot()

        speed = round(
            abs(throttle)
            * self.maximum_speed
        )

        if throttle > 0:
            await asyncio.to_thread(
                robot.forward,
                speed,
            )
            return

        if throttle < 0:
            await asyncio.to_thread(
                robot.backward,
                speed,
            )
            return

        await self._stop_motion()

    async def _stop_motion(self) -> None:
        """
        Stop motor movement without changing steering.

        This is used when the joystick throttle returns to zero while the
        user still owns manual control.
        """

        if self._robot is None:
            return

        await asyncio.to_thread(
            self._robot.stop
        )

    async def _watchdog_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(0.1)

                robot = None

                async with self._lock:
                    if self._owner is None:
                        continue

                    elapsed = (
                        time.monotonic()
                        - self._last_heartbeat
                    )

                    if elapsed <= self.heartbeat_timeout:
                        continue

                    self._owner = None
                    self._last_heartbeat = 0.0
                    self._desired_state = ControlState()
                    self._last_applied_state = None
                    self._state_generation += 1

                    robot = self._robot
                    self._robot = None

                await self._stop_center_close(
                    robot
                )

        except asyncio.CancelledError:
            raise

    def _require_owner(
        self,
        client_id: str,
    ) -> None:
        self._require_open()

        if self._owner != client_id:
            raise DriveControlError(
                "manual drive control is not owned by this client"
            )

    def _require_open(self) -> None:
        if self._closed:
            raise DriveControlError(
                "manual drive controller is closed"
            )

    def _require_robot(
        self,
    ) -> "BetaboxCar":
        if self._robot is None:
            raise DriveControlError(
                "robot is not started"
            )

        return self._robot

    async def _control_loop(self) -> None:
        try:
            while True:
                started = time.monotonic()

                async with self._lock:
                    owner = self._owner
                    robot_ready = self._robot is not None
                    state = self._desired_state
                    generation = self._state_generation
                    last_applied = self._last_applied_state

                if (
                    owner is not None
                    and robot_ready
                    and state != last_applied
                ):
                    try:
                        await self._apply_state(
                            state,
                            generation,
                        )
                    except DriveControlError:
                        # Ownership may have been released
                        # while this iteration was pending.
                        pass

                elapsed = (
                    time.monotonic()
                    - started
                )

                delay = max(
                    0.0,
                    self.update_interval - elapsed,
                )

                await asyncio.sleep(delay)

        except asyncio.CancelledError:
            raise

    async def _generation_is_current(
        self,
        generation: int,
    ) -> bool:
        async with self._lock:
            return (
                generation
                == self._state_generation
            )

    async def _apply_state(
        self,
        state: ControlState,
        generation: int,
    ) -> None:
        async with self._hardware_lock:
            async with self._lock:
                if (
                    self._owner is None
                    or self._robot is None
                    or generation
                    != self._state_generation
                ):
                    return

                previous = (
                    self._last_applied_state
                )

            steering_changed = (
                previous is None
                or state.steering
                != previous.steering
            )

            throttle_changed = (
                previous is None
                or state.throttle
                != previous.throttle
            )

            camera_changed = (
                previous is None
                or state.camera_pan
                != previous.camera_pan
                or state.camera_tilt
                != previous.camera_tilt
            )

            if steering_changed:
                await self._apply_steering_axis(
                    state.steering
                )

            if not await self._generation_is_current(
                generation
            ):
                return

            if throttle_changed:
                await self._apply_throttle(
                    state.throttle
                )

            if not await self._generation_is_current(
                generation
            ):
                return

            if camera_changed:
                await self._apply_camera_axes(
                    state.camera_pan,
                    state.camera_tilt,
                )

            async with self._lock:
                if (
                    self._owner is not None
                    and generation
                    == self._state_generation
                ):
                    self._last_applied_state = (
                        state
                    )
