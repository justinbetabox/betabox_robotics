from __future__ import annotations

import numpy as np

from betabox_robotics.vision import Frame, OverlayRenderer
from betabox_robotics.vision.metadata import Detection, Metadata


def main() -> None:
    print()
    print("Betabox Overlay Test")
    print("====================")
    print()

    frame = Frame.create(np.zeros((240, 320, 3), dtype=np.uint8))

    metadata = Metadata.create(
        "test",
        detections=[
            Detection(
                label="box",
                confidence=0.95,
                box=(50, 40, 100, 80),
                center=(100, 80),
            )
        ],
    )

    renderer = OverlayRenderer()
    output = renderer.draw_metadata(frame, metadata)

    assert output.timestamp == frame.timestamp
    assert output.image.shape == frame.image.shape
    assert output.image.sum() > 0

    print("Overlay renderer test passed.")
    print()


if __name__ == "__main__":
    main()
