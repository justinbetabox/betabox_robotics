#!/usr/bin/env python3

from betabox_robotics.vision import Detection, Metadata, MetadataBus

print("\nMetadata hardware-independent test")
print("==================================")

bus = MetadataBus()

detection = Detection(
    label="red",
    confidence=0.95,
    box=(10, 20, 30, 40),
    center=(25, 40),
)

metadata = Metadata.create(
    source="color",
    detections=[detection],
    data={"count": 1},
)

bus.publish(metadata)

latest = bus.latest("color")
all_latest = bus.all_latest()
history = bus.history()

print(f"latest_source={latest.source if latest else None}")
print(f"latest_count={len(latest.detections) if latest else 0}")
print(f"all_latest_sources={list(all_latest.keys())}")
print(f"history_count={len(history)}")

assert latest is not None
assert latest.source == "color"
assert latest.detections[0].label == "red"
assert latest.detections[0].confidence == 0.95
assert latest.detections[0].box == (10, 20, 30, 40)
assert latest.detections[0].center == (25, 40)
assert latest.data["count"] == 1
assert "color" in all_latest
assert len(history) == 1

bus.clear()

assert bus.latest() is None
assert bus.all_latest() == {}
assert bus.history() == []

print("\nMetadata test complete.")
