import unittest

from betabox_robotics.vision.consumer import FrameConsumer
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.stream import Streamer


class ConcreteConsumer(FrameConsumer):
    def on_frame(self, frame: Frame) -> None:
        self.frame = frame


class ConcreteStreamer(Streamer):
    def __init__(self) -> None:
        self.running = False
        self.frame: Frame | None = None

    def start(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False

    def on_frame(self, frame: Frame) -> None:
        self.frame = frame

    def clients(self) -> int:
        return 0

    def statistics(self) -> dict:
        return {
            "running": self.running,
            "clients": self.clients(),
        }


class VisionInterfaceTests(unittest.TestCase):
    def test_frame_consumer_is_abstract(self) -> None:
        with self.assertRaises(TypeError):
            FrameConsumer()

    def test_concrete_frame_consumer_can_be_created(self) -> None:
        consumer = ConcreteConsumer()
        frame = Frame.create(object())

        consumer.on_frame(frame)

        self.assertIs(consumer.frame, frame)

    def test_streamer_is_abstract(self) -> None:
        with self.assertRaises(TypeError):
            Streamer()

    def test_concrete_streamer_contract(self) -> None:
        streamer = ConcreteStreamer()
        frame = Frame.create(object())

        streamer.start()
        streamer.on_frame(frame)

        self.assertTrue(streamer.running)
        self.assertIs(streamer.frame, frame)
        self.assertEqual(streamer.clients(), 0)
        self.assertEqual(
            streamer.statistics(),
            {
                "running": True,
                "clients": 0,
            },
        )

        streamer.stop()

        self.assertFalse(streamer.running)


if __name__ == "__main__":
    unittest.main()
