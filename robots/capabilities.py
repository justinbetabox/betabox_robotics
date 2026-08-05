from enum import StrEnum


class RobotCapability(StrEnum):
    DRIVE = "drive"
    SENSORS = "sensors"
    VISION = "vision"
    AUDIO = "audio"
    SYSTEM = "system"
