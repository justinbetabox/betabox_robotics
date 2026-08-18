from __future__ import annotations

import os
import secrets
import time
from time import sleep
from typing import Self

from betabox_robotics.calibration import RobotCalibration
from betabox_robotics.camera import CameraMount
from betabox_robotics.drive import Drive
from betabox_robotics.hardware import (
    ADC,
    I2C,
    PWM,
    HardwareError,
    Motor,
    Pin,
    PinMode,
    Servo,
    close_gpio_factory,
)
from betabox_robotics.hardware.ownership import RobotOwnership
from betabox_robotics.robots.defaults import BETABOX_CAR
from betabox_robotics.sensors import (
    Battery,
    Grayscale,
    Ultrasonic,
)

from .errors import (
    RobotRuntimeControlBusyError,
    RobotRuntimeControlError,
)
from .protocol import RuntimeStatus

CONTROL_LEASE_TIMEOUT = 2.0


class RobotRuntime:
    """Long-lived owner of Betabox robot hardware access."""

    _ownership: RobotOwnership
    _running: bool

    _control_owner: str | None
    _control_token: str | None

    _control_expires_at: float | None

    _i2c: I2C | None
    _battery: Battery | None
    _grayscale: Grayscale | None
    _ultrasonic: Ultrasonic | None
    _drive: Drive | None
    _camera_mount: CameraMount | None

    def __init__(
        self,
    ) -> None:
        self._ownership = RobotOwnership(
            owner="Betabox Robot Runtime",
        )

        self._control_owner = None
        self._control_token = None
        self._control_expires_at = None

        self._i2c = None
        self._battery = None
        self._grayscale = None
        self._ultrasonic = None
        self._drive = None
        self._camera_mount = None

        self._running = False

    def _initialize_hardware(
        self,
    ) -> None:
        i2c: I2C | None = None
        battery: Battery | None = None
        grayscale: Grayscale | None = None
        ultrasonic: Ultrasonic | None = None

        left_motor: Motor | None = None
        right_motor: Motor | None = None
        steering: Servo | None = None
        drive: Drive | None = None
        camera_mount: CameraMount | None = None

        try:
            i2c = I2C(
                address=ADC.ADDRESSES,
            )

            battery_config = BETABOX_CAR.sensors.battery

            battery = Battery(
                ADC(
                    battery_config.channel,
                    bus=i2c,
                ),
                scale=battery_config.scale,
                low_voltage=battery_config.low_voltage,
                critical_voltage=battery_config.critical_voltage,
            )

            grayscale_config = BETABOX_CAR.sensors.grayscale

            grayscale = Grayscale(
                left=ADC(
                    grayscale_config.left,
                    bus=i2c,
                ),
                middle=ADC(
                    grayscale_config.middle,
                    bus=i2c,
                ),
                right=ADC(
                    grayscale_config.right,
                    bus=i2c,
                ),
                reference=grayscale_config.reference,
            )

            ultrasonic_config = BETABOX_CAR.sensors.ultrasonic

            ultrasonic = Ultrasonic.default(
                ultrasonic_config,
            )

            drive_config = BETABOX_CAR.drive
            calibration = RobotCalibration.default()

            left_config = drive_config.left_motor
            right_config = drive_config.right_motor
            steering_config = drive_config.steering

            left_motor = Motor(
                PWM(
                    left_config.pwm,
                    bus=i2c,
                ),
                Pin(
                    left_config.direction,
                    mode=PinMode.OUT,
                ),
                reversed=left_config.reversed,
            )

            right_motor = Motor(
                PWM(
                    right_config.pwm,
                    bus=i2c,
                ),
                Pin(
                    right_config.direction,
                    mode=PinMode.OUT,
                ),
                reversed=right_config.reversed,
            )

            steering = Servo(
                steering_config.servo,
                bus=i2c,
                min_angle=steering_config.min_angle,
                max_angle=steering_config.max_angle,
                offset=calibration.steering.offset,
            )

            drive = Drive(
                left_motor=left_motor,
                right_motor=right_motor,
                steering=steering,
                left_trim=calibration.motors.left_trim,
                right_trim=calibration.motors.right_trim,
            )

            camera_mount_config = BETABOX_CAR.camera_mount

            camera_mount = CameraMount.default(
                camera_mount_config,
                pan_offset=calibration.camera_mount.pan_offset,
                tilt_offset=calibration.camera_mount.tilt_offset,
                bus=i2c,
            )

        except (
            HardwareError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ):
            for component in (
                steering,
                right_motor,
                left_motor,
            ):
                if component is None:
                    continue

                try:
                    component.close()
                except (
                    HardwareError,
                    OSError,
                    RuntimeError,
                ):
                    pass

            if ultrasonic is not None:
                try:
                    ultrasonic.close()
                except (
                    HardwareError,
                    OSError,
                    RuntimeError,
                ):
                    pass

            if grayscale is not None:
                try:
                    grayscale.close()
                except (
                    HardwareError,
                    OSError,
                    RuntimeError,
                ):
                    pass

            if battery is not None:
                try:
                    battery.close()
                except (
                    HardwareError,
                    OSError,
                    RuntimeError,
                ):
                    pass

            if i2c is not None:
                try:
                    i2c.close()
                except (
                    HardwareError,
                    OSError,
                    RuntimeError,
                ):
                    pass

            try:
                close_gpio_factory()
            except (
                OSError,
                RuntimeError,
            ):
                pass

            raise

        self._i2c = i2c
        self._battery = battery
        self._grayscale = grayscale
        self._ultrasonic = ultrasonic
        self._drive = drive
        self._camera_mount = camera_mount

    def _close_hardware(
        self,
    ) -> None:
        camera_mount = self._camera_mount
        drive = self._drive
        ultrasonic = self._ultrasonic
        grayscale = self._grayscale
        battery = self._battery
        i2c = self._i2c

        self._camera_mount = None
        self._drive = None
        self._ultrasonic = None
        self._grayscale = None
        self._battery = None
        self._i2c = None

        first_error: HardwareError | OSError | RuntimeError | None = None

        if camera_mount is not None:
            try:
                camera_mount.close()
            except (
                HardwareError,
                OSError,
                RuntimeError,
            ) as exc:
                first_error = exc

        if drive is not None:
            try:
                drive.close()
            except (
                HardwareError,
                OSError,
                RuntimeError,
            ) as exc:
                first_error = exc

        if ultrasonic is not None:
            try:
                ultrasonic.close()
            except (
                HardwareError,
                OSError,
                RuntimeError,
            ) as exc:
                if first_error is None:
                    first_error = exc

        if grayscale is not None:
            try:
                grayscale.close()
            except (
                HardwareError,
                OSError,
                RuntimeError,
            ) as exc:
                if first_error is None:
                    first_error = exc

        if battery is not None:
            try:
                battery.close()
            except (
                HardwareError,
                OSError,
                RuntimeError,
            ) as exc:
                if first_error is None:
                    first_error = exc

        if i2c is not None:
            try:
                i2c.close()
            except (
                HardwareError,
                OSError,
                RuntimeError,
            ) as exc:
                if first_error is None:
                    first_error = exc

        try:
            close_gpio_factory()
        except (
            OSError,
            RuntimeError,
        ) as exc:
            if first_error is None:
                first_error = exc

        if first_error is not None:
            raise first_error

    @staticmethod
    def _validate_control_owner(
        owner: object,
    ) -> str:
        if not isinstance(
            owner,
            str,
        ):
            raise TypeError("control owner must be a string")

        result = owner.strip()

        if not result:
            raise ValueError("control owner cannot be empty")

        return result

    def _require_control(
        self,
        token: str,
    ) -> Drive:

        if not token:
            raise ValueError("control token cannot be empty")

        if self._control_expired():
            self._expire_control()

        current_token = self._control_token

        if current_token is None:
            raise RobotRuntimeControlError("robot control has not been acquired")

        if not secrets.compare_digest(
            token,
            current_token,
        ):
            raise RobotRuntimeControlError("invalid robot control token")

        drive = self._drive

        if drive is None:
            raise RuntimeError("drive hardware is not initialized")

        return drive

    def _clear_control(
        self,
    ) -> None:
        self._control_owner = None
        self._control_token = None
        self._control_expires_at = None

    def _control_expired(
        self,
    ) -> bool:
        expires_at = self._control_expires_at

        if expires_at is None:
            return False

        return time.monotonic() >= expires_at

    def _expire_control(
        self,
    ) -> None:
        """Emergency-stop and clear an expired control lease."""

        if self._control_token is None:
            return

        drive = self._drive

        try:
            if drive is not None:
                drive.emergency_stop()
        finally:
            self._clear_control()

    def poll(
        self,
    ) -> None:
        """Perform periodic runtime safety checks."""

        if not self._running:
            return

        if self._control_expired():
            self._expire_control()

    @property
    def running(
        self,
    ) -> bool:
        return self._running

    def acquire_control(
        self,
        owner: str,
    ) -> str:
        """Acquire exclusive logical control of the robot."""

        if not self._running:
            raise RuntimeError("robot runtime is not running")

        if self._drive is None:
            raise RuntimeError("drive hardware is not initialized")

        owner_value = self._validate_control_owner(owner)

        if self._control_token is not None:
            current_owner = self._control_owner or "unknown"

            raise RobotRuntimeControlBusyError(
                f"robot control is already owned by {current_owner}"
            )

        token = secrets.token_urlsafe(32)

        self._control_owner = owner_value
        self._control_token = token
        self._control_expires_at = time.monotonic() + CONTROL_LEASE_TIMEOUT

        return token

    def release_control(
        self,
        token: str,
    ) -> None:
        """Safely stop the robot and release logical control."""

        if not token:
            raise ValueError("control token cannot be empty")

        current_token = self._control_token

        if current_token is None:
            raise RobotRuntimeControlError("robot control is not currently acquired")

        if not secrets.compare_digest(
            token,
            current_token,
        ):
            raise RobotRuntimeControlError("invalid robot control token")

        drive = self._drive

        if drive is None:
            raise RuntimeError("drive hardware is not initialized")

        # Releasing control must always leave the motors physically stopped.
        drive.emergency_stop()
        self._clear_control()

        self._control_owner = None
        self._control_token = None

    def renew_control(
        self,
        token: str,
    ) -> None:
        """Renew the current control lease."""

        _ = self._require_control(token)

        self._control_expires_at = time.monotonic() + CONTROL_LEASE_TIMEOUT

    def start(
        self,
    ) -> None:
        """Acquire physical hardware ownership and initialize runtime hardware."""

        if self._running:
            return

        self._ownership.acquire()

        try:
            self._initialize_hardware()
        except (
            HardwareError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ):
            self._ownership.release()
            raise

        self._running = True

    def stop(
        self,
    ) -> None:
        """Close runtime hardware and release robot ownership."""

        if not self._running:
            return

        self._running = False

        shutdown_error: HardwareError | OSError | RuntimeError | None = None

        try:
            self._close_hardware()
        except (
            HardwareError,
            OSError,
            RuntimeError,
        ) as exc:
            shutdown_error = exc
        finally:
            self._control_owner = None
            self._control_token = None
            self._clear_control()
            self._ownership.release()

        if shutdown_error is not None:
            raise shutdown_error

    def battery_voltage(
        self,
    ) -> float:
        """Return the current battery voltage."""

        if not self._running:
            raise RuntimeError("robot runtime is not running")

        battery = self._battery

        if battery is None:
            raise RuntimeError("battery hardware is not initialized")

        return battery.voltage()

    def grayscale_values(
        self,
    ) -> tuple[int, int, int]:
        """Return the current grayscale sensor values."""

        if not self._running:
            raise RuntimeError("robot runtime is not running")

        grayscale = self._grayscale

        if grayscale is None:
            raise RuntimeError("grayscale hardware is not initialized")

        values = grayscale.read()

        if len(values) != 3:
            raise RuntimeError(
                "grayscale sensor returned an unexpected number of values"
            )

        return (
            values[0],
            values[1],
            values[2],
        )

    def ultrasonic_distance(
        self,
        *,
        samples: int = 10,
    ) -> float:
        """Return the current ultrasonic distance in centimeters."""

        if not self._running:
            raise RuntimeError("robot runtime is not running")

        ultrasonic = self._ultrasonic

        if ultrasonic is None:
            raise RuntimeError("ultrasonic hardware is not initialized")

        return ultrasonic.distance(
            samples=samples,
        )

    def status(
        self,
    ) -> RuntimeStatus:
        """Return the current runtime state."""

        return RuntimeStatus(
            ready=self._running,
            ownership_acquired=self._ownership.acquired,
            hardware_initialized=(
                self._i2c is not None
                and self._battery is not None
                and self._grayscale is not None
                and self._ultrasonic is not None
                and self._drive is not None
                and self._camera_mount is not None
            ),
            control_owner=self._control_owner,
            pid=os.getpid(),
        )

    def drive_status(
        self,
    ) -> dict[str, bool | float]:
        """Return the current drive subsystem status."""

        if not self._running:
            raise RuntimeError("robot runtime is not running")

        drive = self._drive

        if drive is None:
            raise RuntimeError("drive hardware is not initialized")

        return drive.status().to_dict()

    def camera_mount_status(
        self,
    ) -> dict[str, float | None]:
        """Return the current camera mount status."""

        if not self._running:
            raise RuntimeError("robot runtime is not running")

        camera_mount = self._camera_mount

        if camera_mount is None:
            raise RuntimeError("camera mount hardware is not initialized")

        return camera_mount.status().to_dict()

    def drive_stop(
        self,
        token: str,
    ) -> None:
        """Stop the drive subsystem for the current control owner."""

        drive = self._require_control(token)

        drive.stop()

    def steering_center(
        self,
        token: str,
    ) -> None:
        """Center the steering for the current control owner."""

        drive = self._require_control(token)

        drive.center()

    def steering_left(
        self,
        token: str,
        *,
        angle: float = 30,
    ) -> None:
        """Turn steering left for the current control owner."""

        drive = self._require_control(token)

        drive.left(
            angle,
        )

    def steering_right(
        self,
        token: str,
        *,
        angle: float = 30,
    ) -> None:
        """Turn steering right for the current control owner."""

        drive = self._require_control(token)

        drive.right(
            angle,
        )

    def steering_angle(
        self,
        token: str,
        angle: float,
    ) -> None:
        """Set the logical steering angle for the current control owner."""

        drive = self._require_control(token)

        drive.steering.move_to(angle)

    def drive_forward(
        self,
        token: str,
        *,
        speed: float = 20,
    ) -> None:
        """Drive forward for the current control owner."""

        drive = self._require_control(token)

        drive.forward(
            speed,
        )

    def drive_backward(
        self,
        token: str,
        *,
        speed: float = 20,
    ) -> None:
        """Drive backward for the current control owner."""

        drive = self._require_control(token)

        drive.backward(
            speed,
        )

    def camera_pan(
        self,
        token: str,
        angle: float,
        *,
        smooth: bool = True,
    ) -> None:
        """Pan the camera mount for the current control owner."""

        _ = self._require_control(token)

        camera_mount = self._camera_mount

        if camera_mount is None:
            raise RuntimeError("camera mount hardware is not initialized")

        camera_mount.pan(
            angle,
            smooth=smooth,
        )

    def camera_tilt(
        self,
        token: str,
        angle: float,
        *,
        smooth: bool = True,
    ) -> None:
        """Tilt the camera mount for the current control owner."""

        _ = self._require_control(token)

        camera_mount = self._camera_mount

        if camera_mount is None:
            raise RuntimeError("camera mount hardware is not initialized")

        camera_mount.tilt(
            angle,
            smooth=smooth,
        )

    def camera_center(
        self,
        token: str,
        *,
        smooth: bool = True,
    ) -> None:
        """Center the camera mount for the current control owner."""

        _ = self._require_control(token)

        camera_mount = self._camera_mount

        if camera_mount is None:
            raise RuntimeError("camera mount hardware is not initialized")

        camera_mount.center(
            smooth=smooth,
        )

    def preview_steering_calibration(
        self,
        token: str,
        offset: float,
    ) -> None:
        drive = self._require_control(token)

        original_offset = drive.steering.offset

        try:
            drive.steering.offset = offset
            drive.center()

        finally:
            drive.steering.offset = original_offset

    def preview_camera_calibration(
        self,
        token: str,
        *,
        pan_offset: float,
        tilt_offset: float,
    ) -> None:
        _ = self._require_control(token)

        camera_mount = self._camera_mount

        if camera_mount is None:
            raise RuntimeError("camera mount hardware is not initialized")

        original_pan_offset = camera_mount.pan_offset
        original_tilt_offset = camera_mount.tilt_offset

        try:
            camera_mount.pan_servo.offset = pan_offset
            camera_mount.tilt_servo.offset = tilt_offset

            camera_mount.center()

        finally:
            camera_mount.pan_servo.offset = original_pan_offset
            camera_mount.tilt_servo.offset = original_tilt_offset

    def preview_motor_calibration(
        self,
        token: str,
        *,
        left_trim: float,
        right_trim: float,
        steering_offset: float,
    ) -> None:
        drive = self._require_control(token)

        original_left_trim = drive.left_trim
        original_right_trim = drive.right_trim
        original_steering_offset = drive.steering.offset

        try:
            drive.left_trim = left_trim
            drive.right_trim = right_trim
            drive.steering.offset = steering_offset

            drive.center()

            try:
                drive.forward(25)
                sleep(1.5)

            finally:
                drive.stop()

        finally:
            drive.left_trim = original_left_trim
            drive.right_trim = original_right_trim
            drive.steering.offset = original_steering_offset

    def close(
        self,
    ) -> None:
        self.stop()

    def __enter__(
        self,
    ) -> Self:
        self.start()

        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()
