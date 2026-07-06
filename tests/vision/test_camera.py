#!/usr/bin/env python3

from betabox_robotics.vision import CameraManager

with CameraManager() as camera:
    print("\nCamera hardware test")
    print("====================")

    frame = camera.capture_frame()

    print(f"running={camera.is_running()}")
    print(f"timestamp={frame.timestamp}")
    print(f"image_type={type(frame.image)}")

    if hasattr(frame.image, "shape"):
        print(f"image_shape={frame.image.shape}")

print("\nCamera hardware test complete.")
