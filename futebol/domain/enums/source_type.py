from enum import StrEnum


class SourceType(StrEnum):
    OFFICIAL = "official"
    PUBLIC_LEGAL = "public/free/legal"
    USER_PROVIDED = "user-provided"
    UNKNOWN = "unknown"
    BLOCKED_REJECTED = "blocked/rejected"
