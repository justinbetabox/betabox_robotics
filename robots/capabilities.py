from enum import Enum


class RobotCapability(str, Enum):
    DRIVE = "drive"
    SENSORS = "sensors"
    VISION = "vision"
    AUDIO = "audio"
    SYSTEM = "system"
