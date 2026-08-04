import unittest

from betabox_robotics.vision.detector import Detector
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Metadata


class TestDetector(Detector):
    def detect(
        self,
        frame: Frame,
    ) -> Metadata | None:
        return None


class DetectorTests(unittest.TestCase):
    def test_default_state(self) -> None:
        detector = TestDetector("test")

        self.assertEqual(detector.name, "test")
        self.assertFalse(detector.enabled)

    def test_enable_disable(self) -> None:
        detector = TestDetector("test")

        detector.enable()
        self.assertTrue(detector.enabled)

        detector.disable()
        self.assertFalse(detector.enabled)

    def test_name_is_trimmed(self) -> None:
        detector = TestDetector("  color  ")

        self.assertEqual(detector.name, "color")

    def test_rejects_empty_name(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "detector name cannot be empty",
        ):
            TestDetector(" ")

    def test_rejects_non_string_name(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "detector name must be a string",
        ):
            TestDetector(123)  # type: ignore[arg-type]

    def test_rejects_non_boolean_enabled(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "enabled must be a boolean",
        ):
            TestDetector(
                "test",
                enabled=1,  # type: ignore[arg-type]
            )


if __name__ == "__main__":
    unittest.main()
