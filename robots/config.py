from dataclasses import dataclass

from betabox_robotics.hardware import (
    AnalogChannel,
    DigitalPin,
    PWMChannel,
)


@dataclass(frozen=True)
class MotorConfig:
    pwm: PWMChannel
    direction: DigitalPin
    reversed: bool = False
    trim: float = 1.0


@dataclass(frozen=True)
class SteeringConfig:
    servo: PWMChannel
    min_angle: float = -30
    max_angle: float = 30


@dataclass(frozen=True)
class DriveConfig:
    left_motor: MotorConfig
    right_motor: MotorConfig
    steering: SteeringConfig


@dataclass(frozen=True)
class UltrasonicConfig:
    trigger: DigitalPin
    echo: DigitalPin
    timeout: float = 0.02


@dataclass(frozen=True)
class GrayscaleConfig:
    left: AnalogChannel
    middle: AnalogChannel
    right: AnalogChannel
    reference: tuple[int, int, int] = (1000, 1000, 1000)


@dataclass(frozen=True)
class BatteryConfig:
    channel: AnalogChannel
    scale: float = 3.0
    low_voltage: float = 6.6
    critical_voltage: float = 6.2


@dataclass(frozen=True)
class SensorsConfig:
    ultrasonic: UltrasonicConfig
    grayscale: GrayscaleConfig
    battery: BatteryConfig


@dataclass(frozen=True)
class VisionConfig:
    service_url: str = "http://127.0.0.1:8080"
    request_timeout: float = 10.0

    def __post_init__(self):
        if not self.service_url:
            raise ValueError("service_url cannot be empty")
        if self.request_timeout <= 0:
            raise ValueError("request_timeout must be greater than 0")


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class SystemConfig:
    media_root: str | None = None


@dataclass(frozen=True)
class RobotConfig:
    drive: DriveConfig
    sensors: SensorsConfig
    vision: VisionConfig = VisionConfig()
    audio: AudioConfig = AudioConfig()
    system: SystemConfig = SystemConfig()
