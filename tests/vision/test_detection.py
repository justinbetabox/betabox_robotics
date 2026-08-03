import unittest
from unittest.mock import MagicMock

from betabox_robotics.vision.detection import (
    DetectionError,
    DetectionManager,
)
from betabox_robotics.vision.detector import Detector
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Metadata
from betabox_robotics.vision.metadata_bus import MetadataBus


class StubDetector(Detector):
    def __init__(
        self,
        name: str,
        *,
        enabled: bool = False,
        result: Metadata | None = None,
        error: Exception | None = None,
    ) -> None:
        super().__init__(
            name,
            enabled=enabled,
        )
        self.result = result
        self.error = error
        self.frames: list[Frame] = []

    def detect(self, frame: Frame) -> Metadata | None:
        self.frames.append(frame)

        if self.error is not None:
            raise self.error

        return self.result


class DetectionManagerTests(unittest.TestCase):
    def setUp(self):
        self.bus = MagicMock(spec=MetadataBus)
        self.manager = DetectionManager(self.bus)
        self.frame = Frame.create(object())

    def test_default_detectors_are_registered(self):
        self.assertEqual(
            self.manager.names(),
            [
                self.manager.color.name,
                self.manager.face.name,
                self.manager.objects.name,
            ],
        )

    def test_default_detectors_are_disabled(self):
        for name in self.manager.names():
            self.assertFalse(self.manager.is_enabled(name))

    def test_register_detector(self):
        detector = StubDetector("custom")

        self.manager.register(detector)

        self.assertIn(
            "custom",
            self.manager.names(),
        )

    def test_duplicate_registration_raises(self):
        detector = StubDetector("custom")

        self.manager.register(detector)

        with self.assertRaisesRegex(
            DetectionError,
            "detector already registered: custom",
        ):
            self.manager.register(StubDetector("custom"))

    def test_unregister_detector(self):
        detector = StubDetector("custom")
        self.manager.register(detector)

        self.manager.unregister("custom")

        self.assertNotIn(
            "custom",
            self.manager.names(),
        )

    def test_unregister_unknown_detector_is_noop(self):
        self.manager.unregister("missing")

        self.assertNotIn(
            "missing",
            self.manager.names(),
        )

    def test_enable_detector(self):
        detector = StubDetector("custom")
        self.manager.register(detector)

        self.manager.enable("custom")

        self.assertTrue(detector.enabled)
        self.assertTrue(self.manager.is_enabled("custom"))

    def test_disable_detector(self):
        detector = StubDetector(
            "custom",
            enabled=True,
        )
        self.manager.register(detector)

        self.manager.disable("custom")

        self.assertFalse(detector.enabled)
        self.assertFalse(self.manager.is_enabled("custom"))

    def test_unknown_detector_raises(self):
        with self.assertRaisesRegex(
            DetectionError,
            "unknown detector: missing",
        ):
            self.manager.enable("missing")

    def test_disabled_detector_is_skipped(self):
        detector = StubDetector("custom")
        self.manager.register(detector)

        self.manager.on_frame(self.frame)

        self.assertEqual(detector.frames, [])
        self.bus.publish.assert_not_called()

    def test_enabled_detector_receives_frame(self):
        detector = StubDetector(
            "custom",
            enabled=True,
        )
        self.manager.register(detector)

        self.manager.on_frame(self.frame)

        self.assertEqual(
            detector.frames,
            [self.frame],
        )

    def test_metadata_is_published(self):
        metadata = Metadata(
            source="custom",
            timestamp=self.frame.timestamp,
        )

        detector = StubDetector(
            "custom",
            enabled=True,
            result=metadata,
        )
        self.manager.register(detector)

        self.manager.on_frame(self.frame)

        self.bus.publish.assert_called_once_with(metadata)

    def test_none_metadata_is_not_published(self):
        detector = StubDetector(
            "custom",
            enabled=True,
            result=None,
        )
        self.manager.register(detector)

        self.manager.on_frame(self.frame)

        self.bus.publish.assert_not_called()

    def test_detector_error_is_wrapped(self):
        detector = StubDetector(
            "custom",
            enabled=True,
            error=RuntimeError("boom"),
        )
        self.manager.register(detector)

        with self.assertRaisesRegex(
            DetectionError,
            "custom detector failed: boom",
        ):
            self.manager.on_frame(self.frame)

    def test_later_detectors_run_after_earlier_failure(self):
        first = StubDetector(
            "first",
            enabled=True,
            error=RuntimeError("boom"),
        )

        metadata = Metadata(
            source="second",
            timestamp=self.frame.timestamp,
        )

        second = StubDetector(
            "second",
            enabled=True,
            result=metadata,
        )

        self.manager.register(first)
        self.manager.register(second)

        with self.assertRaisesRegex(
            DetectionError,
            "first detector failed: boom",
        ):
            self.manager.on_frame(self.frame)

        self.assertEqual(
            second.frames,
            [self.frame],
        )
        self.bus.publish.assert_called_once_with(metadata)

    def test_only_first_error_is_reported(self):
        first = StubDetector(
            "first",
            enabled=True,
            error=RuntimeError("first failure"),
        )
        second = StubDetector(
            "second",
            enabled=True,
            error=RuntimeError("second failure"),
        )

        self.manager.register(first)
        self.manager.register(second)

        with self.assertRaisesRegex(
            DetectionError,
            "first detector failed: first failure",
        ):
            self.manager.on_frame(self.frame)

        self.assertEqual(
            second.frames,
            [self.frame],
        )


if __name__ == "__main__":
    unittest.main()
    import unittest
    from unittest.mock import MagicMock

    from betabox_robotics.vision.detection import (
        DetectionError,
        DetectionManager,
    )
    from betabox_robotics.vision.detector import Detector
    from betabox_robotics.vision.frame import Frame
    from betabox_robotics.vision.metadata import Metadata
    from betabox_robotics.vision.metadata_bus import MetadataBus

    class StubDetector(Detector):
        def __init__(
            self,
            name: str,
            *,
            enabled: bool = False,
            result: Metadata | None = None,
            error: Exception | None = None,
        ) -> None:
            super().__init__(
                name,
                enabled=enabled,
            )
            self.result = result
            self.error = error
            self.frames: list[Frame] = []

        def detect(self, frame: Frame) -> Metadata | None:
            self.frames.append(frame)

            if self.error is not None:
                raise self.error

            return self.result

    class DetectionManagerTests(unittest.TestCase):
        def setUp(self):
            self.bus = MagicMock(spec=MetadataBus)
            self.manager = DetectionManager(self.bus)
            self.frame = Frame.create(object())

        def test_default_detectors_are_registered(self):
            self.assertEqual(
                self.manager.names(),
                [
                    self.manager.color.name,
                    self.manager.face.name,
                    self.manager.objects.name,
                ],
            )

        def test_default_detectors_are_disabled(self):
            for name in self.manager.names():
                self.assertFalse(self.manager.is_enabled(name))

        def test_register_detector(self):
            detector = StubDetector("custom")

            self.manager.register(detector)

            self.assertIn(
                "custom",
                self.manager.names(),
            )

        def test_duplicate_registration_raises(self):
            detector = StubDetector("custom")

            self.manager.register(detector)

            with self.assertRaisesRegex(
                DetectionError,
                "detector already registered: custom",
            ):
                self.manager.register(StubDetector("custom"))

        def test_unregister_detector(self):
            detector = StubDetector("custom")
            self.manager.register(detector)

            self.manager.unregister("custom")

            self.assertNotIn(
                "custom",
                self.manager.names(),
            )

        def test_unregister_unknown_detector_is_noop(self):
            self.manager.unregister("missing")

            self.assertNotIn(
                "missing",
                self.manager.names(),
            )

        def test_enable_detector(self):
            detector = StubDetector("custom")
            self.manager.register(detector)

            self.manager.enable("custom")

            self.assertTrue(detector.enabled)
            self.assertTrue(self.manager.is_enabled("custom"))

        def test_disable_detector(self):
            detector = StubDetector(
                "custom",
                enabled=True,
            )
            self.manager.register(detector)

            self.manager.disable("custom")

            self.assertFalse(detector.enabled)
            self.assertFalse(self.manager.is_enabled("custom"))

        def test_unknown_detector_raises(self):
            with self.assertRaisesRegex(
                DetectionError,
                "unknown detector: missing",
            ):
                self.manager.enable("missing")

        def test_disabled_detector_is_skipped(self):
            detector = StubDetector("custom")
            self.manager.register(detector)

            self.manager.on_frame(self.frame)

            self.assertEqual(detector.frames, [])
            self.bus.publish.assert_not_called()

        def test_enabled_detector_receives_frame(self):
            detector = StubDetector(
                "custom",
                enabled=True,
            )
            self.manager.register(detector)

            self.manager.on_frame(self.frame)

            self.assertEqual(
                detector.frames,
                [self.frame],
            )

        def test_metadata_is_published(self):
            metadata = Metadata(
                source="custom",
                timestamp=self.frame.timestamp,
            )

            detector = StubDetector(
                "custom",
                enabled=True,
                result=metadata,
            )
            self.manager.register(detector)

            self.manager.on_frame(self.frame)

            self.bus.publish.assert_called_once_with(metadata)

        def test_none_metadata_is_not_published(self):
            detector = StubDetector(
                "custom",
                enabled=True,
                result=None,
            )
            self.manager.register(detector)

            self.manager.on_frame(self.frame)

            self.bus.publish.assert_not_called()

        def test_detector_error_is_wrapped(self):
            detector = StubDetector(
                "custom",
                enabled=True,
                error=RuntimeError("boom"),
            )
            self.manager.register(detector)

            with self.assertRaisesRegex(
                DetectionError,
                "custom detector failed: boom",
            ):
                self.manager.on_frame(self.frame)

        def test_later_detectors_run_after_earlier_failure(self):
            first = StubDetector(
                "first",
                enabled=True,
                error=RuntimeError("boom"),
            )

            metadata = Metadata(
                source="second",
                timestamp=self.frame.timestamp,
            )

            second = StubDetector(
                "second",
                enabled=True,
                result=metadata,
            )

            self.manager.register(first)
            self.manager.register(second)

            with self.assertRaisesRegex(
                DetectionError,
                "first detector failed: boom",
            ):
                self.manager.on_frame(self.frame)

            self.assertEqual(
                second.frames,
                [self.frame],
            )
            self.bus.publish.assert_called_once_with(metadata)

        def test_only_first_error_is_reported(self):
            first = StubDetector(
                "first",
                enabled=True,
                error=RuntimeError("first failure"),
            )
            second = StubDetector(
                "second",
                enabled=True,
                error=RuntimeError("second failure"),
            )

            self.manager.register(first)
            self.manager.register(second)

            with self.assertRaisesRegex(
                DetectionError,
                "first detector failed: first failure",
            ):
                self.manager.on_frame(self.frame)

            self.assertEqual(
                second.frames,
                [self.frame],
            )

    if __name__ == "__main__":
        unittest.main()
