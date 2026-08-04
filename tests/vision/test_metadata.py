import unittest

from betabox_robotics.vision.metadata import Detection, Metadata
from betabox_robotics.vision.metadata_bus import MetadataBus


class MetadataTests(unittest.TestCase):
    def test_create_converts_detections_to_tuple(self) -> None:
        detection = Detection(label="red")

        metadata = Metadata.create(
            "color",
            detections=[detection],
        )

        self.assertEqual(metadata.detections, (detection,))

    def test_create_accepts_source_frame_timestamp(self) -> None:
        metadata = Metadata.create(
            "color",
            timestamp=123.5,
        )

        self.assertEqual(metadata.timestamp, 123.5)

    def test_create_copies_data_dictionary(self) -> None:
        data = {"threshold": 10}

        metadata = Metadata.create("color", data=data)
        data["threshold"] = 20

        self.assertEqual(metadata.data["threshold"], 10)


class MetadataBusTests(unittest.TestCase):
    def test_rejects_invalid_history_size(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "max_history must be greater than zero",
        ):
            MetadataBus(max_history=0)

    def test_rejects_non_integer_history_size(self) -> None:
        for value in (
            True,
            1.5,
            "10",
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(TypeError),
            ):
                MetadataBus(max_history=value)  # type: ignore[arg-type]

    def test_publish_requires_metadata(self) -> None:
        bus = MetadataBus()

        with self.assertRaises(TypeError):
            bus.publish(object())  # type: ignore[arg-type]

    def test_latest_returns_most_recent_metadata(self) -> None:
        bus = MetadataBus()
        first = Metadata.create("color", timestamp=1.0)
        second = Metadata.create("face", timestamp=2.0)

        bus.publish(first)
        bus.publish(second)

        self.assertIs(bus.latest(), second)
        self.assertIs(bus.latest("color"), first)

    def test_latest_rejects_non_string_source(self) -> None:
        bus = MetadataBus()

        with self.assertRaises(TypeError):
            bus.latest(123)  # type: ignore[arg-type]

    def test_history_zero_returns_empty_sequence(self) -> None:
        bus = MetadataBus()
        bus.publish(Metadata.create("color"))

        self.assertEqual(bus.history(limit=0), ())

    def test_history_limit_returns_newest_items(self) -> None:
        bus = MetadataBus()
        first = Metadata.create("color", timestamp=1.0)
        second = Metadata.create("color", timestamp=2.0)
        third = Metadata.create("color", timestamp=3.0)

        bus.publish(first)
        bus.publish(second)
        bus.publish(third)

        self.assertEqual(bus.history(limit=2), (second, third))

    def test_history_rejects_negative_limit(self) -> None:
        bus = MetadataBus()

        with self.assertRaisesRegex(
            ValueError,
            "limit must be zero or greater",
        ):
            bus.history(limit=-1)

    def test_history_rejects_non_integer_limit(self) -> None:
        bus = MetadataBus()

        for value in (
            True,
            1.5,
            "2",
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(TypeError),
            ):
                bus.history(limit=value)  # type: ignore[arg-type]

    def test_history_is_bounded(self) -> None:
        bus = MetadataBus(max_history=2)
        first = Metadata.create("color", timestamp=1.0)
        second = Metadata.create("color", timestamp=2.0)
        third = Metadata.create("color", timestamp=3.0)

        bus.publish(first)
        bus.publish(second)
        bus.publish(third)

        self.assertEqual(bus.history(), (second, third))

    def test_clear_removes_latest_and_history(self) -> None:
        bus = MetadataBus()
        bus.publish(Metadata.create("color"))

        bus.clear()

        self.assertIsNone(bus.latest())
        self.assertEqual(bus.all_latest(), {})
        self.assertEqual(bus.history(), ())
