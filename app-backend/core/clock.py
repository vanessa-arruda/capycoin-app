from datetime import UTC, datetime


def now() -> datetime:
    """Current UTC time. Tests replace this to move time forward."""
    return datetime.now(UTC)
