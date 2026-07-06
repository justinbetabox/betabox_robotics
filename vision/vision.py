from betabox_robotics.vision.consumer import FrameConsumer
from betabox_robotics.vision.detection import DetectionManager
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.frame_source import FrameSource
from betabox_robotics.vision.metadata_bus import MetadataBus
from betabox_robotics.vision.recording import RecordingService
from betabox_robotics.vision.snapshot import SnapshotService


class Vision:
    """
    Vision subsystem container.

    Owns the FrameSource and MetadataBus. FrameSource owns CameraManager.
    Streaming, detection, and recording consume frames from FrameSource.
    Snapshots use the latest available frame through the FrameProvider
    interface. Detectors publish structured results to MetadataBus.
    """

    def __init__(
        self,
        frame_source: FrameSource | None = None,
        metadata_bus: MetadataBus | None = None,
    ) -> None:
        self.frame_source = frame_source or FrameSource()
        self.metadata = metadata_bus or MetadataBus()
        self.detection = DetectionManager(self.metadata)
        self.snapshot = SnapshotService(self.frame_source)
        self.recording = RecordingService()
        self.register_consumer(self.recording)
        self.register_consumer(self.detection)

    @classmethod
    def default(cls, robot_config=None) -> "Vision":
        return cls()

    def start(self) -> None:
        self.frame_source.start()

    def stop(self) -> None:
        self.frame_source.stop()

    def is_running(self) -> bool:
        return self.frame_source.is_running()

    def latest_frame(self) -> Frame:
        return self.frame_source.latest_frame()

    def register_consumer(self, consumer: FrameConsumer) -> None:
        self.frame_source.register_consumer(consumer)

    def unregister_consumer(self, consumer: FrameConsumer) -> None:
        self.frame_source.unregister_consumer(consumer)

    def close(self) -> None:
        self.stop()

    def deinit(self) -> None:
        self.close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
