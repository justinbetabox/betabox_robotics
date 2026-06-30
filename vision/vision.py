from betabox_car.vision.frame import Frame
from betabox_car.vision.frame_source import FrameSource
from betabox_car.vision.metadata_bus import MetadataBus


class Vision:
    """
    Vision subsystem container.

    Owns the FrameSource and MetadataBus. FrameSource owns CameraManager.
    Streaming, detection, snapshots, and recording will consume frames
    from FrameSource. Detectors publish structured results to MetadataBus.
    """

    def __init__(
        self,
        frame_source: FrameSource | None = None,
        metadata_bus: MetadataBus | None = None,
    ) -> None:
        self.frame_source = frame_source or FrameSource()
        self.metadata = metadata_bus or MetadataBus()

    def start(self) -> None:
        self.frame_source.start()

    def stop(self) -> None:
        self.frame_source.stop()

    def is_running(self) -> bool:
        return self.frame_source.is_running()

    def latest_frame(self) -> Frame:
        return self.frame_source.latest_frame()

    def close(self) -> None:
        self.stop()

    def deinit(self) -> None:
        self.close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
