#!/usr/bin/env python3

from time import sleep

from betabox_robotics.vision import Frame, FrameConsumer, FrameSource


class CountingConsumer(FrameConsumer):
    def __init__(self):
        self.count = 0
        self.latest = None

    def on_frame(self, frame: Frame) -> None:
        self.count += 1
        self.latest = frame


consumer = CountingConsumer()

with FrameSource(fps=10) as source:
    print("\nFrameConsumer hardware test")
    print("===========================")

    source.register_consumer(consumer)

    sleep(1.0)

    print(f"consumer_count={source.consumer_count()}")
    print(f"frames_received={consumer.count}")

    if consumer.latest is not None:
        print(f"latest_timestamp={consumer.latest.timestamp}")

    source.unregister_consumer(consumer)

    print(f"consumer_count_after_unregister={source.consumer_count()}")

print("\nFrameConsumer hardware test complete.")
