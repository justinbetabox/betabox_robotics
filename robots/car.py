from pathlib import Path
from typing import Any

from .capabilities import RobotCapability
from .health import HealthCheck, RobotHealth
from .robot import Robot

from betabox_robotics.vision import ClientRecording, ClientSnapshot, VisionClient


class CarRobot(Robot):
    """
    Base class for car-style Betabox robots.

    Concrete car implementations are responsible for constructing their
    hardware-backed subsystems.

    This class also provides beginner-friendly convenience methods that
    delegate to the underlying subsystem APIs.
    """

    capabilities = {
        RobotCapability.DRIVE,
        RobotCapability.SENSORS,
        RobotCapability.VISION,
        RobotCapability.AUDIO,
        RobotCapability.SYSTEM,
    }

    drive: Any
    sensors: Any
    vision: VisionClient
    audio: Any
    system: Any

    def forward(self, speed: float) -> None:
        self.drive.forward(speed)

    def backward(self, speed: float) -> None:
        self.drive.backward(speed)

    def stop(self) -> None:
        self.drive.stop()

    def left(self, angle: float = 30) -> None:
        self.drive.left(angle)

    def right(self, angle: float = 30) -> None:
        self.drive.right(angle)

    def center(self) -> None:
        self.drive.center()

    def say(self, text: str) -> None:
        self.audio.say(text)

    def play(self, sound) -> None:
        self.audio.play(sound)

    def play_note(self, note_or_frequency, duration: float) -> None:
        self.audio.play_note(note_or_frequency, duration)

    def play_melody(self, notes, *, gap: float = 0.0) -> None:
        self.audio.play_melody(notes, gap=gap)

    def stop_audio(self) -> None:
        self.audio.stop()

    def is_audio_playing(self) -> bool:
        return self.audio.is_playing()

    # Ultrasonic
    def distance(self, samples: int = 10) -> float:
        return self.sensors.ultrasonic.distance(samples)

    # Battery
    def battery_voltage(self) -> float:
        return self.sensors.battery.voltage()

    def is_battery_low(self) -> bool:
        return self.sensors.battery.is_low()

    def is_battery_critical(self) -> bool:
        return self.sensors.battery.is_critical()

    def battery_status(self) -> str:
        return self.sensors.battery.status()

    # Line sensor
    def line_status(self, threshold: float = 0.5) -> list[int]:
        return self.sensors.grayscale.status(threshold=threshold)

    def line_values(self) -> list[int]:
        return self.sensors.grayscale.read()

    def line_normalized(self) -> list[float]:
        return self.sensors.grayscale.normalized()

    def is_vision_running(self) -> bool:
        return bool(self.vision.statistics().get("running", False))

    def snapshot(
        self,
        *,
        filename: str | None = None,
        overlay: bool = False,
        source: str | None = None,
    ) -> ClientSnapshot:
        return self.vision.snapshot(
            filename=filename,
            overlay=overlay,
            source=source,
        )

    def capture(
        self,
        *,
        filename: str | None = None,
        overlay: bool = False,
        source: str | None = None,
    ) -> ClientSnapshot:
        return self.snapshot(
            filename=filename,
            overlay=overlay,
            source=source,
        )

    def start_recording(
        self,
        *,
        filename: str | None = None,
        overlay: bool = False,
        source: str | None = None,
    ) -> Path:
        return self.vision.start_recording(
            filename=filename,
            overlay=overlay,
            source=source,
        )

    def stop_recording(self) -> ClientRecording:
        return self.vision.stop_recording()

    def is_recording(self) -> bool:
        stats = self.vision.statistics()
        recording = stats.get("recording", {})
        return bool(recording.get("active", False))

    def vision_stats(self) -> dict[str, Any]:
        return self.vision.statistics()

    def metadata(self, source: str | None = None) -> dict[str, Any]:
        return self.vision.metadata(source)

    def enable_detection(self, name: str) -> None:
        return self.vision.enable_detection(name)

    def disable_detection(self, name: str) -> None:
        return self.vision.disable_detection(name)

    def detection_status(self) -> dict[str, Any]:
        return self.vision.detection_status()

    def enable_stream_overlay(self, source: str | None = None) -> None:
        return self.vision.enable_stream_overlay(source)

    def disable_stream_overlay(self) -> None:
        return self.vision.disable_stream_overlay()

    def hostname(self) -> str:
        return self.system.hostname()

    def ip_addresses(self) -> list[str]:
        return self.system.ip_addresses()

    def media_paths(self):
        return self.system.media_paths()

    def ensure_media_paths(self):
        return self.system.ensure_media_paths()

    def status(self):
        return self.system.status()

    def health(self):
        checks = []

        system_health = self.system.health()
        checks.append(
            HealthCheck(
                name="system",
                ok=system_health.ok,
                message="; ".join(system_health.messages),
            )
        )

        battery_critical = self.is_battery_critical()
        battery_status = self.battery_status()

        checks.append(
            HealthCheck(
                name="battery",
                ok=not battery_critical,
                message=f"battery status: {battery_status}" if battery_critical else "",
            )
        )

        return RobotHealth(
            ok=all(check.ok for check in checks),
            checks=checks,
        )

    def stop_all(self) -> None:
        self.drive.stop()

        try:
            if self.is_recording():
                self.stop_recording()
        except Exception:
            pass

        try:
            self.stop_audio()
        except Exception:
            pass

        system_stop_all = getattr(self.system, "stop_all", None)
        if callable(system_stop_all):
            system_stop_all()

        self._started = False
