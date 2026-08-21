from __future__ import annotations

from betabox_robotics.hardware import Pins

from .config import (
    AudioConfig,
    BatteryConfig,
    CameraMountConfig,
    DriveConfig,
    GrayscaleConfig,
    MotorConfig,
    RobotConfig,
    SensorsConfig,
    SteeringConfig,
    SystemConfig,
    UltrasonicConfig,
    VisionConfig,
)

BETABOX_CAR = RobotConfig(
    drive=DriveConfig(
        left_motor=MotorConfig(
            pwm=Pins.P13,
            direction=Pins.D4,
            reversed=True,
            trim=1.0,
        ),
        right_motor=MotorConfig(
            pwm=Pins.P12,
            direction=Pins.D5,
            reversed=False,
            trim=1.0,
        ),
        steering=SteeringConfig(
            servo=Pins.P2,
            min_angle=-30,
            max_angle=30,
        ),
    ),
    sensors=SensorsConfig(
        ultrasonic=UltrasonicConfig(
            trigger=Pins.D2,
            echo=Pins.D3,
            timeout=0.02,
        ),
        grayscale=GrayscaleConfig(
            left=Pins.A0,
            middle=Pins.A1,
            right=Pins.A2,
            reference=(
                1000,
                1000,
                1000,
            ),
        ),
        battery=BatteryConfig(
            channel=Pins.A4,
            scale=3.0,
            low_voltage=6.6,
            critical_voltage=6.2,
        ),
    ),
    camera_mount=CameraMountConfig(
        pan_servo=Pins.P0,
        tilt_servo=Pins.P1,
        pan_min_angle=-45.0,
        pan_max_angle=45.0,
        tilt_min_angle=-30.0,
        tilt_max_angle=45.0,
        pan_center=0.0,
        tilt_center=0.0,
        pan_reversed=True,
        tilt_reversed=True,
    ),
    vision=VisionConfig(),
    audio=AudioConfig(),
    system=SystemConfig(),
)
