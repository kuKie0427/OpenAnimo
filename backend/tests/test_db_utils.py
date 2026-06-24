from __future__ import annotations

from datetime import UTC, datetime


def test_utcnow_returns_naive_datetime():
    from app.db.utils import utcnow

    result = utcnow()
    assert isinstance(result, datetime)
    assert result.tzinfo is None


def test_utcnow_is_close_to_now():
    from app.db.utils import utcnow

    result = utcnow()
    expected = datetime.now(UTC).replace(tzinfo=None)
    delta = abs((result - expected).total_seconds())
    assert delta < 1.0
