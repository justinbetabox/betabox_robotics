import cv2

from betabox_car.vision.detector import Detector
from betabox_car.vision.frame import Frame
from betabox_car.vision.metadata import Detection, Metadata


class FaceDetector(Detector):
    """
    Detects faces in frames and returns structured metadata.

    This detector does not draw overlays. It returns face locations as
    metadata for other components to display, store, or ignore.
    """

    def __init__(
        self,
        *,
        enabled: bool = False,
        scale_factor: float = 1.1,
        min_neighbors: int = 5,
        min_size: tuple[int, int] = (30, 30),
    ) -> None:
        super().__init__("face", enabled=enabled)

        self.scale_factor = scale_factor
        self.min_neighbors = min_neighbors
        self.min_size = min_size

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._cascade = cv2.CascadeClassifier(cascade_path)

        if self._cascade.empty():
            raise ValueError(f"failed to load face cascade: {cascade_path}")

    def configure(
        self,
        *,
        scale_factor: float | None = None,
        min_neighbors: int | None = None,
        min_size: tuple[int, int] | None = None,
    ) -> None:
        if scale_factor is not None:
            self.scale_factor = float(scale_factor)

        if min_neighbors is not None:
            self.min_neighbors = int(min_neighbors)

        if min_size is not None:
            self.min_size = min_size

    def enable(
        self,
        *,
        scale_factor: float | None = None,
        min_neighbors: int | None = None,
        min_size: tuple[int, int] | None = None,
    ) -> None:
        self.configure(
            scale_factor=scale_factor,
            min_neighbors=min_neighbors,
            min_size=min_size,
        )
        self.enabled = True

    def detect(self, frame: Frame) -> Metadata:
        image = frame.image

        if len(image.shape) != 3 or image.shape[2] != 3:
            return Metadata.create(
                self.name,
                data={
                    "count": 0,
                    "error": "expected 3-channel image",
                },
            )

        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        faces = self._cascade.detectMultiScale(
            gray,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
            minSize=self.min_size,
        )

        detections: list[Detection] = []

        for x, y, width, height in faces:
            center = (int(x + width // 2), int(y + height // 2))

            detections.append(
                Detection(
                    label="face",
                    confidence=None,
                    box=(int(x), int(y), int(width), int(height)),
                    center=center,
                    data={
                        "width": int(width),
                        "height": int(height),
                    },
                )
            )

        return Metadata.create(
            self.name,
            detections=detections,
            data={
                "count": len(detections),
            },
        )
