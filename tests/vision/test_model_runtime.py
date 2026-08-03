import unittest

from betabox_robotics.vision.model_runtime import ModelDetection


class ModelDetectionTests(unittest.TestCase):
    def test_model_detection_fields(self) -> None:
        detection = ModelDetection(
            label="person",
            confidence=0.9,
            box=(1, 2, 3, 4),
            data={"class_id": 1},
        )

        self.assertEqual(detection.label, "person")
        self.assertEqual(detection.confidence, 0.9)
        self.assertEqual(detection.box, (1, 2, 3, 4))
        self.assertEqual(detection.data, {"class_id": 1})


if __name__ == "__main__":
    unittest.main()
