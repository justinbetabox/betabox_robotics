import unittest

from betabox_robotics.vision.detector import Detector
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Metadata


class StubDetector(Detector):
    def detect(self, frame: Frame) -> Metadata | None:
        return None


class DetectorTests(unittest.TestCase):
    def test_cannot_instantiate_abstract_detector(self):
        with self.assertRaises(TypeError):
            Detector("test")

    def test_name_is_stripped(self):
        detector = StubDetector("  color  ")

        self.assertEqual(detector.name, "color")

    def test_empty_name_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "detector name cannot be empty",
        ):
            StubDetector("   ")

    def test_disabled_by_default(self):
        detector = StubDetector("test")

        self.assertFalse(detector.enabled)

    def test_can_start_enabled(self):
        detector = StubDetector(
            "test",
            enabled=True,
        )

        self.assertTrue(detector.enabled)

    def test_enable(self):
        detector = StubDetector("test")

        detector.enable()

        self.assertTrue(detector.enabled)

    def test_disable(self):
        detector = StubDetector(
            "test",
            enabled=True,
        )

        detector.disable()

        self.assertFalse(detector.enabled)


if __name__ == "__main__":
    unittest.main()
