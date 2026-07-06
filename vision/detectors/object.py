from betabox_robotics.vision.detector import Detector
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Detection, Metadata
from betabox_robotics.vision.model_runtime import ObjectDetectionRuntime


class ObjectDetector(Detector):
    """
    Detects objects using a pluggable object detection runtime.

    The runtime owns model-specific inference details. ObjectDetector
    adapts model results into Betabox Vision metadata.
    """

    def __init__(
        self,
        runtime: ObjectDetectionRuntime | None = None,
        *,
        enabled: bool = False,
        min_confidence: float = 0.5,
    ) -> None:
        super().__init__("objects", enabled=enabled)
        self.runtime = runtime
        self.min_confidence = float(min_confidence)

    def configure(
        self,
        *,
        runtime: ObjectDetectionRuntime | None = None,
        min_confidence: float | None = None,
    ) -> None:
        if runtime is not None:
            self.runtime = runtime

        if min_confidence is not None:
            self.min_confidence = float(min_confidence)

    def enable(
        self,
        *,
        runtime: ObjectDetectionRuntime | None = None,
        min_confidence: float | None = None,
    ) -> None:
        self.configure(runtime=runtime, min_confidence=min_confidence)
        self.enabled = True

    def detect(self, frame: Frame) -> Metadata:
        if self.runtime is None:
            return Metadata.create(
                self.name,
                data={
                    "count": 0,
                    "error": "object detection runtime is not configured",
                },
            )

        model_detections = self.runtime.detect(frame)

        detections: list[Detection] = []

        for result in model_detections:
            if result.confidence < self.min_confidence:
                continue

            x, y, width, height = result.box
            center = (x + width // 2, y + height // 2)

            detections.append(
                Detection(
                    label=result.label,
                    confidence=result.confidence,
                    box=result.box,
                    center=center,
                    data=result.data,
                )
            )

        return Metadata.create(
            self.name,
            detections=detections,
            data={
                "count": len(detections),
                "min_confidence": self.min_confidence,
            },
        )
