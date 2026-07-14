from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from math import isfinite

from betabox_robotics import Robot


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
        *,
        heartbeat_timeout: float = 1.0,
        update_hz: float = 20.0,
        maximum_speed: int = 100,
        steering_angle: float = 30.0,
    ) -> None:
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
        self._control_task: asyncio.Task | None = None
        self._watchdog_task: asyncio.Task | None = None
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

    async def start(self) -> None:
        if self._watchdog_task is None:
            self._watchdog_task = asyncio.create_task(
                self._watchdog_loop(),
                name="LaunchpadDriveWatchdog",
            )

        if self._control_task is None:
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

            return True

        except Exception:
            async with self._lock:
                if self._owner == client_id:
                    self._owner = None

                self._last_heartbeat = 0.0

            raise

        finally:
            async with self._lock:
                if self._claiming == client_id:
                    self._claiming = None

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

            self._desired_state = ControlState()
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

        await self._safe_neutralize()

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
            results = await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )

            for result in results:
                if isinstance(
                    result,
                    asyncio.CancelledError,
                ):
                    continue

                if isinstance(result, Exception):
                    # Cleanup must continue even if a worker
                    # had already failed.
                    pass

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

        if robot is not None:
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

                await asyncio.to_thread(
                    robot.close
                )

    async def _ensure_robot(self) -> None:
        if self._robot is not None:
            return

        robot = Robot.default()

        try:
            await asyncio.to_thread(
                robot.start
            )
        except Exception:
            await asyncio.to_thread(
                robot.close
            )
            raise

        self._robot = robot

    async def _safe_neutralize(self) -> None:
        """
        Stop movement and center steering.

        Used for emergency stop, disconnect, ownership release, watchdog
        timeout, and application shutdown.
        """

        if self._robot is None:
            return

        try:
            await asyncio.to_thread(
                self._robot.stop
            )
        finally:
            try:
                await asyncio.to_thread(
                    self._robot.center
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

                should_neutralize = False

                async with self._lock:
                    if self._owner is None:
                        continue

                    elapsed = (
                        time.monotonic()
                        - self._last_heartbeat
                    )

                    if elapsed > self.heartbeat_timeout:
                        self._owner = None
                        self._last_heartbeat = 0.0
                        self._desired_state = ControlState()
                        self._last_applied_state = None
                        self._state_generation += 1
                        should_neutralize = True

                if should_neutralize:
                    await self._safe_neutralize()

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

    def _require_robot(self):
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
                    await self._apply_state(
                        state,
                        generation,
                    )

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

    async def _apply_state(
        self,
        state: ControlState,
        generation: int,
    ) -> None:
        await self._apply_steering_axis(
            state.steering
        )

        async with self._lock:
            if generation != self._state_generation:
                return

        await self._apply_throttle(
            state.throttle
        )

        async with self._lock:
            if generation == self._state_generation:
                self._last_applied_state = state
