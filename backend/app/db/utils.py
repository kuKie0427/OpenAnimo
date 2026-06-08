from __future__ import annotations

from datetime import datetime, timezone

UTC = timezone.utc


def utcnow() -> datetime:
    """Return current UTC time without timezone info (compatible with PostgreSQL TIMESTAMP WITHOUT TIME ZONE)."""
    return datetime.now(UTC).replace(tzinfo=None)
