from pathlib import Path

from betabox_robotics.audio import (
    Audio,
    AudioStatus,
    MelodyNote,
    NoteValue,
)
from betabox_robotics.drive import Drive
from betabox_robotics.sensors import Sensors
from betabox_robotics.system import MediaPaths, System, SystemStatus, SystemHealth
from betabox_robotics.vision import (
    ClientDetectionStatus,
    ClientMetadata,
    ClientRecording,
    ClientSnapshot,
    ClientStreamOverlayStatus,
    VisionClient,
    ClientVisionStatistics,
)

from .capabilities import RobotCapability
from .health import HealthCheck, RobotHealth
from .robot import Robot


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

    drive: Drive
    sensors: Sensors
    vision: VisionClient
    audio: Audio
    system: System

    def __init__(self) -> None:
        super().__init__()
        self._recording_started_by_robot = False

    def forward(self, speed: float) -> None:
        self._require_ready()
        self.drive.forward(speed)

    def backward(self, speed: float) -> None:
        self._require_ready()
        self.drive.backward(speed)

    def stop(self) -> None:
        self._require_ready()
        self.drive.stop()

    def left(self, angle: float = 30) -> None:
        self._require_ready()
        self.drive.left(angle)

    def right(self, angle: float = 30) -> None:
        self._require_ready()
        self.drive.right(angle)

    def center(self) -> None:
        self._require_ready()
        self.drive.center()

    def say(self, text: str) -> None:
        self._require_ready()
        self.audio.say(text)

    def play(self, sound: str | Path) -> None:
        self._require_ready()
        self.audio.play(sound)

    def play_note(self, note_or_frequency: NoteValue, duration: float) -> None:
        self._require_ready()
        self.audio.play_note(note_or_frequency, duration)

    def play_melody(self, notes: list[MelodyNote], *, gap: float = 0.0) -> None:
        self._require_ready()
        self.audio.play_melody(notes, gap=gap)

    def stop_audio(self) -> None:
        self._require_ready()
        self.audio.stop()

    def is_audio_playing(self) -> bool:
        self._require_ready()
        return self.audio.is_playing()

    # Ultrasonic
    def distance(self, samples: int = 10) -> float:
        self._require_ready()
        return self.sensors.ultrasonic.distance(samples)

    # Battery
    def battery_voltage(self) -> float:
        self._require_ready()
        return self.sensors.battery.voltage()

    def is_battery_low(self) -> bool:
        self._require_ready()
        return self.sensors.battery.is_low()

    def is_battery_critical(self) -> bool:
        self._require_ready()
        return self.sensors.battery.is_critical()

    def battery_status(self) -> str:
        self._require_ready()
        return self.sensors.battery.status()

    # Line sensor
    def line_status(self, threshold: float = 0.5) -> list[int]:
        self._require_ready()
        return self.sensors.grayscale.status(threshold=threshold)

    def line_values(self) -> list[int]:
        self._require_ready()
        return self.sensors.grayscale.read()

    def line_normalized(self) -> list[float]:
        self._require_ready()
        return self.sensors.grayscale.normalized()

    def is_vision_running(self) -> bool:
        self._require_ready()
        return self.vision.statistics().running

    def snapshot(
        self,
        *,
        filename: str | None = None,
        overlay: bool = False,
        source: str | None = None,
    ) -> ClientSnapshot:
        self._require_ready()
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
        self._require_ready()

        path = self.vision.start_recording(
            filename=filename,
            overlay=overlay,
            source=source,
        )

        self._recording_started_by_robot = True
        return path

    def stop_recording(self) -> ClientRecording:
        self._require_ready()

        recording = self.vision.stop_recording()
        self._recording_started_by_robot = False
        return recording

    def is_recording(self) -> bool:
        self._require_ready()
        return self.vision.statistics().recording.active

    def vision_stats(self) -> ClientVisionStatistics:
        self._require_ready()
        return self.vision.statistics()

    def metadata(self, source: str | None = None) -> ClientMetadata | None:
        self._require_ready()
        return self.vision.metadata(source)

    def enable_detection(self, name: str) -> ClientDetectionStatus:
        self._require_ready()
        return self.vision.enable_detection(name)

    def disable_detection(self, name: str) -> ClientDetectionStatus:
        self._require_ready()
        return self.vision.disable_detection(name)

    def detection_status(self) -> ClientDetectionStatus:
        self._require_ready()
        return self.vision.detection_status()

    def enable_stream_overlay(
        self,
        source: str | None = None,
    ) -> ClientStreamOverlayStatus:
        self._require_ready()
        return self.vision.enable_stream_overlay(source)

    def disable_stream_overlay(
        self,
    ) -> ClientStreamOverlayStatus:
        self._require_ready()
        return self.vision.disable_stream_overlay()

    def hostname(self) -> str:
        self._require_ready()
        return self.system.hostname()

    def ip_addresses(self) -> list[str]:
        self._require_ready()
        return self.system.ip_addresses()

    def media_paths(self) -> MediaPaths:
        self._require_ready()
        return self.system.media_paths()

    def ensure_media_paths(self) -> MediaPaths:
        self._require_ready()
        return self.system.ensure_media_paths()

    def status(self) -> SystemStatus:
        self._require_ready()
        return self.system.status()

    def system_status(self) -> SystemStatus:
        self._require_ready()
        return self.system.status()

    def health(self) -> RobotHealth:
        self._require_ready()
        checks: list[HealthCheck] = []

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

    def system_health(self) -> SystemHealth:
        self._require_ready()
        return self.system.health()

    def audio_status(self) -> AudioStatus:
        self._require_ready()
        return self.audio.status()

    def stop_all(self) -> None:
        self.require_open()

        if self._recording_started_by_robot:
            try:
                self.vision.stop_recording()
            except Exception:
                pass
            finally:
                self._recording_started_by_robot = False

        try:
            self.drive.stop()
        except Exception:
            pass

        try:
            self.audio.stop()
        except Exception:
            pass

        system_stop_all = getattr(self.system, "stop_all", None)

        if callable(system_stop_all):
            try:
                system_stop_all()
            except Exception:
                pass

        self._started = False

    def _require_ready(self) -> None:
        self.require_started()
