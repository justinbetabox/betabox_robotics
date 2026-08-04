import unittest
from unittest.mock import MagicMock, patch

from betabox_robotics.vision.detection import (
    DetectionError,
    DetectionManager,
    _validate_detector_name,
)
from betabox_robotics.vision.detector import (
    Detector,
    DetectorError,
)
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Metadata
from betabox_robotics.vision.metadata_bus import MetadataBus


class FakeDetector(Detector):
    def __init__(
        self,
        name: str,
        *,
        enabled: bool = False,
        metadata: Metadata | None = None,
    ) -> None:
        super().__init__(
            name,
            enabled=enabled,
        )
        self.metadata = metadata
        self.frames: list[Frame] = []

    def detect(
        self,
        frame: Frame,
    ) -> Metadata | None:
        self.frames.append(frame)
        return self.metadata


class FailingDetector(Detector):
    def __init__(
        self,
        name: str,
        *,
        enabled: bool = True,
        message: str = "boom",
    ) -> None:
        super().__init__(
            name,
            enabled=enabled,
        )
        self.message = message
        self.frames: list[Frame] = []

    def detect(
        self,
        frame: Frame,
    ) -> Metadata | None:
        self.frames.append(frame)
        raise DetectorError(self.message)


class DetectionValidationTests(unittest.TestCase):
    def test_validate_detector_name(self) -> None:
        self.assertEqual(
            _validate_detector_name("  color  "),
            "color",
        )

    def test_validate_detector_name_rejects_non_string(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "detector name must be a string",
        ):
            _validate_detector_name(123)

    def test_validate_detector_name_rejects_empty_name(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "detector name cannot be empty",
        ):
            _validate_detector_name(" ")


class DetectionManagerTests(unittest.TestCase):
    def _create_manager(
        self,
    ) -> tuple[
        DetectionManager,
        MagicMock,
        MagicMock,
        MagicMock,
    ]:
        color = MagicMock(spec=Detector)
        color.name = "color"
        color.enabled = False

        face = MagicMock(spec=Detector)
        face.name = "face"
        face.enabled = False

        objects = MagicMock(spec=Detector)
        objects.name = "objects"
        objects.enabled = False

        with (
            patch(
                "betabox_robotics.vision.detection.ColorDetector",
                return_value=color,
            ),
            patch(
                "betabox_robotics.vision.detection.FaceDetector",
                return_value=face,
            ),
            patch(
                "betabox_robotics.vision.detection.ObjectDetector",
                return_value=objects,
            ),
        ):
            manager = DetectionManager(MetadataBus())

        return (
            manager,
            color,
            face,
            objects,
        )

    def test_requires_metadata_bus(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "metadata_bus must be a MetadataBus",
        ):
            DetectionManager(
                object(),  # type: ignore[arg-type]
            )

    def test_registers_default_detectors(self) -> None:
        manager, color, face, objects = self._create_manager()

        self.assertEqual(
            manager.names(),
            [
                "color",
                "face",
                "objects",
            ],
        )
        self.assertIs(
            manager.color,
            color,
        )
        self.assertIs(
            manager.face,
            face,
        )
        self.assertIs(
            manager.objects,
            objects,
        )

    def test_register_requires_detector(self) -> None:
        manager, _, _, _ = self._create_manager()

        with self.assertRaisesRegex(
            TypeError,
            "detector must be a Detector instance",
        ):
            manager.register(
                object(),  # type: ignore[arg-type]
            )

    def test_register_adds_detector(self) -> None:
        manager, _, _, _ = self._create_manager()
        detector = FakeDetector("custom")

        manager.register(detector)

        self.assertIn(
            "custom",
            manager.names(),
        )

    def test_register_rejects_duplicate_name(self) -> None:
        manager, _, _, _ = self._create_manager()

        with self.assertRaisesRegex(
            DetectionError,
            "detector already registered: color",
        ):
            manager.register(FakeDetector("color"))

    def test_unregister_removes_detector(self) -> None:
        manager, _, _, _ = self._create_manager()

        manager.unregister("face")

        self.assertNotIn(
            "face",
            manager.names(),
        )

    def test_unregister_unknown_detector_does_not_raise(
        self,
    ) -> None:
        manager, _, _, _ = self._create_manager()

        manager.unregister("missing")

        self.assertEqual(
            manager.names(),
            [
                "color",
                "face",
                "objects",
            ],
        )

    def test_enable_enables_named_detector(self) -> None:
        manager, color, _, _ = self._create_manager()

        manager.enable("color")

        color.enable.assert_called_once_with()

    def test_disable_disables_named_detector(self) -> None:
        manager, color, _, _ = self._create_manager()

        manager.disable("color")

        color.disable.assert_called_once_with()

    def test_is_enabled_returns_detector_state(self) -> None:
        manager, color, _, _ = self._create_manager()
        color.enabled = True

        self.assertTrue(manager.is_enabled("color"))

    def test_unknown_detector_raises(self) -> None:
        manager, _, _, _ = self._create_manager()

        with self.assertRaisesRegex(
            DetectionError,
            "unknown detector: missing",
        ):
            manager.enable("missing")

    def test_enable_color_forwards_configuration(self) -> None:
        manager, color, _, _ = self._create_manager()

        custom_ranges = {
            "team_marker": (
                (
                    (10, 100, 100),
                    (20, 255, 255),
                ),
            ),
        }

        manager.enable_color(
            [
                "red",
                "team_marker",
            ],
            custom_ranges=custom_ranges,
            min_area=25,
        )

        color.enable.assert_called_once_with(
            [
                "red",
                "team_marker",
            ],
            custom_ranges=custom_ranges,
            min_area=25,
        )


class DetectionManagerFrameTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = MetadataBus()

        with (
            patch(
                "betabox_robotics.vision.detection.ColorDetector",
                return_value=FakeDetector("color"),
            ),
            patch(
                "betabox_robotics.vision.detection.FaceDetector",
                return_value=FakeDetector("face"),
            ),
            patch(
                "betabox_robotics.vision.detection.ObjectDetector",
                return_value=FakeDetector("objects"),
            ),
        ):
            self.manager = DetectionManager(self.bus)

    def test_on_frame_requires_frame(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "frame must be a Frame instance",
        ):
            self.manager.on_frame(
                object(),  # type: ignore[arg-type]
            )

    def test_disabled_detectors_are_skipped(self) -> None:
        frame = Frame.create(object())

        self.manager.on_frame(frame)

        self.assertEqual(
            self.bus.history(),
            (),
        )

        for detector in (
            self.manager.color,
            self.manager.face,
            self.manager.objects,
        ):
            self.assertEqual(
                detector.frames,
                [],
            )

    def test_enabled_detector_metadata_is_published(
        self,
    ) -> None:
        metadata = Metadata.create(
            "color",
            timestamp=123.5,
        )
        detector = FakeDetector(
            "custom",
            enabled=True,
            metadata=metadata,
        )
        self.manager.register(detector)

        frame = Frame.create(
            object(),
            timestamp=123.5,
        )

        self.manager.on_frame(frame)

        self.assertEqual(
            detector.frames,
            [frame],
        )
        self.assertIs(
            self.bus.latest("color"),
            metadata,
        )

    def test_none_metadata_is_ignored(self) -> None:
        detector = FakeDetector(
            "custom",
            enabled=True,
            metadata=None,
        )
        self.manager.register(detector)

        self.manager.on_frame(Frame.create(object()))

        self.assertEqual(
            self.bus.history(),
            (),
        )

    def test_failure_does_not_prevent_later_detector(
        self,
    ) -> None:
        failing = FailingDetector(
            "failing",
            message="first failure",
        )
        metadata = Metadata.create("working")
        working = FakeDetector(
            "working",
            enabled=True,
            metadata=metadata,
        )

        self.manager.register(failing)
        self.manager.register(working)

        frame = Frame.create(object())

        with self.assertRaisesRegex(
            DetectionError,
            ("failing detector failed: first failure"),
        ) as context:
            self.manager.on_frame(frame)

        self.assertEqual(
            failing.frames,
            [frame],
        )
        self.assertEqual(
            working.frames,
            [frame],
        )
        self.assertIs(
            self.bus.latest("working"),
            metadata,
        )
        self.assertIsInstance(
            context.exception.__cause__,
            DetectorError,
        )
        self.assertEqual(
            str(context.exception.__cause__),
            "first failure",
        )

    def test_first_detector_failure_is_preserved(
        self,
    ) -> None:
        first = FailingDetector(
            "first",
            message="failure one",
        )
        second = FailingDetector(
            "second",
            message="failure two",
        )

        self.manager.register(first)
        self.manager.register(second)

        with self.assertRaisesRegex(
            DetectionError,
            "first detector failed: failure one",
        ) as context:
            self.manager.on_frame(Frame.create(object()))

        self.assertIsInstance(
            context.exception.__cause__,
            DetectorError,
        )
        self.assertEqual(
            str(context.exception.__cause__),
            "failure one",
        )


if __name__ == "__main__":
    unittest.main()
