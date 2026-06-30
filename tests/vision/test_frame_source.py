#!/usr/bin/env python3

from time import sleep

from betabox_car.vision import FrameSource

with FrameSource(fps=10) as source:
    print("\nFrameSource hardware test")
    print("=========================")

    sleep(1.0)

    frame = source.latest_frame()

    print(f"running={source.is_running()}")
    print(f"timestamp={frame.timestamp}")
    print(f"image_type={type(frame.image)}")

    if hasattr(frame.image, "shape"):
        print(f"image_shape={frame.image.shape}")

    if source.last_error() is not None:
        print(f"last_error={source.last_error()}")

print("\nFrameSource hardware test complete.")
