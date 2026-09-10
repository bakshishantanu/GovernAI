from datetime import datetime, timedelta, timezone

from app.api.v1.costs import _since_for


def test_all_window_has_no_since_cutoff():
    assert _since_for("all") is None


def test_24h_window_is_roughly_24_hours_back():
    since = _since_for("24h")
    delta = datetime.now(timezone.utc) - since
    assert timedelta(hours=23, minutes=59) < delta < timedelta(hours=24, minutes=1)


def test_7d_window_is_roughly_seven_days_back():
    since = _since_for("7d")
    delta = datetime.now(timezone.utc) - since
    assert timedelta(days=6, hours=23) < delta < timedelta(days=7, hours=1)


def test_30d_window_is_roughly_thirty_days_back():
    since = _since_for("30d")
    delta = datetime.now(timezone.utc) - since
    assert timedelta(days=29, hours=23) < delta < timedelta(days=30, hours=1)
