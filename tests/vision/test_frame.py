import unittest
from unittest.mock import patch

from betabox_robotics.vision.frame import Frame


class FrameTests(unittest.TestCase):
    def test_create_uses_supplied_timestamp(self) -> None:
        image = object()

        frame = Frame.create(
            image,
            timestamp=123.5,
        )

        self.assertIs(frame.image, image)
        self.assertEqual(frame.timestamp, 123.5)

    def test_create_uses_current_time_when_omitted(self) -> None:
        image = object()

        with patch(
            "betabox_robotics.vision.frame.time",
            return_value=456.25,
        ):
            frame = Frame.create(image)

        self.assertIs(frame.image, image)
        self.assertEqual(frame.timestamp, 456.25)


if __name__ == "__main__":
    unittest.main()
