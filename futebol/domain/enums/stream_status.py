from enum import StrEnum


class StreamStatus(StrEnum):
    UNCHECKED = "unchecked"
    ALIVE = "alive"
    BROKEN = "broken"
    UNREACHABLE = "unreachable"
    UNKNOWN = "unknown"
