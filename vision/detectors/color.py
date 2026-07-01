import cv2

from betabox_car.vision.detector import Detector
from betabox_car.vision.frame import Frame
from betabox_car.vision.metadata import Detection, Metadata


class ColorDetector(Detector):
    """
    Detects colored regions in frames and publishes metadata.

    This detector does not draw overlays. It returns structured metadata
    that other components can display, store, or ignore.
    """

    DEFAULT_RANGES = {
        "red": [
            ((0, 120, 70), (10, 255, 255)),
            ((170, 120, 70), (180, 255, 255)),
        ],
        "green": [
            ((35, 80, 80), (85, 255, 255)),
        ],
        "blue": [
            ((90, 80, 80), (130, 255, 255)),
        ],
        "yellow": [
            ((20, 100, 100), (35, 255, 255)),
        ],
    }

    def __init__(
        self,
        colors: str | list[str] = "red",
        *,
        min_area: float = 500.0,
        enabled: bool = False,
    ) -> None:
        super().__init__("color:red", enabled=enabled)

        self.colors: list[str] = []
        self.min_area = 500.0

        self.configure(colors, min_area=min_area)

    def detect(self, frame: Frame) -> Metadata:
        image = frame.image

        if len(image.shape) != 3 or image.shape[2] != 3:
            return Metadata.create(
                self.name,
                data={
                    "colors": self.colors,
                    "count": 0,
                    "counts": {color: 0 for color in self.colors},
                    "error": "expected 3-channel image",
                },
            )

        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)

        all_detections: list[Detection] = []
        counts: dict[str, int] = {}

        for color in self.colors:
            detections = self._detect_color(hsv, color)
            counts[color] = len(detections)
            all_detections.extend(detections)

        all_detections.sort(
            key=lambda detection: detection.data.get("area", 0),
            reverse=True,
        )

        return Metadata.create(
            self.name,
            detections=all_detections,
            data={
                "colors": self.colors,
                "count": len(all_detections),
                "counts": counts,
            },
        )

    def _detect_color(self, hsv, color: str) -> list[Detection]:
        mask = None

        for lower, upper in self.DEFAULT_RANGES[color]:
            current = cv2.inRange(hsv, lower, upper)
            mask = current if mask is None else cv2.bitwise_or(mask, current)

        assert mask is not None

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        detections: list[Detection] = []

        for contour in contours:
            area = cv2.contourArea(contour)

            if area < self.min_area:
                continue

            x, y, width, height = cv2.boundingRect(contour)
            center = (x + width // 2, y + height // 2)

            detections.append(
                Detection(
                    label=color,
                    confidence=None,
                    box=(x, y, width, height),
                    center=center,
                    data={"area": area, "color": color},
                )
            )

        return detections

    def configure(
        self,
        colors: str | list[str],
        *,
        min_area: float | None = None,
    ) -> None:
        color_list = [colors] if isinstance(colors, str) else list(colors)

        if not color_list:
            raise ValueError("at least one color is required")

        unsupported = [
            color for color in color_list if color not in self.DEFAULT_RANGES
        ]

        if unsupported:
            raise ValueError(f"unsupported color(s): {', '.join(unsupported)}")

        self.colors = color_list

        if min_area is not None:
            self.min_area = float(min_area)

        self.name = "color" if len(color_list) > 1 else f"color:{color_list[0]}"

    def enable(
        self,
        colors: str | list[str] | None = None,
        *,
        min_area: float | None = None,
    ) -> None:
        if colors is not None:
            self.configure(colors, min_area=min_area)

        self.enabled = True
