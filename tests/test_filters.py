"""Unit tests for engine/config.py's Jinja filters."""
from engine.config import _longdate, env


def test_longdate_formats_an_iso_date_with_no_leading_zero():
    assert _longdate("2026-09-07") == "September 7, 2026"


def test_longdate_drops_the_leading_zero_on_a_single_digit_day():
    assert _longdate("2026-01-01") == "January 1, 2026"


def test_longdate_handles_a_double_digit_day():
    assert _longdate("2026-12-25") == "December 25, 2026"


def test_longdate_returns_unparseable_input_unchanged():
    assert _longdate("not a date") == "not a date"
    assert _longdate("2026-13-40") == "2026-13-40"  # invalid month/day
    assert _longdate("") == ""


def test_longdate_returns_none_unchanged():
    # meta.updated / latest_log_date can be None (see engine/pipeline.py's
    # latest_log_date and engine/profile.py's optional fields); the filter
    # must not raise when a template applies it under a falsy guard that
    # still evaluates the expression eagerly elsewhere.
    assert _longdate(None) is None


def test_longdate_is_registered_as_a_jinja_filter():
    assert env.filters["longdate"] is _longdate


def test_longdate_filter_works_from_a_template():
    template = env.from_string("{{ value|longdate }}")
    assert template.render(value="2026-09-07") == "September 7, 2026"
