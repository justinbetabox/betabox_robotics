import unittest

from betabox_robotics.vision.consumer import FrameConsumer
from betabox_robotics.vision.frame import Frame


class TestConsumer(FrameConsumer):
    def __init__(self) -> None:
        self.frames: list[Frame] = []

    def on_frame(
        self,
        frame: Frame,
    ) -> None:
        self.frames.append(frame)


class FrameConsumerTests(unittest.TestCase):
    def test_abstract_consumer_cannot_be_instantiated(self) -> None:
        with self.assertRaises(TypeError):
            FrameConsumer()

    def test_concrete_consumer_receives_frame(self) -> None:
        consumer = TestConsumer()
        frame = Frame.create(object())

        consumer.on_frame(frame)

        self.assertEqual(
            consumer.frames,
            [frame],
        )


if __name__ == "__main__":
    unittest.main()
