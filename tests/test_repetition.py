# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
"""Tests for the repetition module."""
from datetime import datetime

from dontforget.repetition import next_dates


def test_simple_patterns_with_every_each():
    """Test simple repetition patterns using "every" and "each"."""
    base_date = datetime(1980, 9, 20, 8, 8, 8)
    mapping = {
        datetime(1980, 9, 21, 8, 8, 8): ('Each 1 day', '1 day', '1d'),
        datetime(1980, 9, 23, 8, 8, 8): ('Every 3 days', '3day', '3d'),
        datetime(1980, 10, 20, 8, 8, 8): ('Every 1 month', '1 month', '1mo'),
        datetime(1980, 11, 20, 8, 8, 8): ('Each 2 months', '2monthS', '2 mo'),
        datetime(1982, 9, 20, 8, 8, 8): ('Every 2 years', '2years', '2 y'),
        datetime(1980, 11, 1, 8, 8, 8): ('EACH 6 WEEKS', '6WEEK', '6 w'),
        datetime(1980, 9, 20, 9, 8, 8): ('Every1hour', '1hours', '1h'),
        datetime(1980, 9, 20, 12, 8, 8): ('EACH 4 HOURS', '4hours', '4h'),
        datetime(1980, 9, 20, 8, 23, 8): ('every 15 minute', '15 minute', '15mi', '15 mi', '15 min')
    }
    for expected_date, natural_patterns in mapping.items():
        for natural_pattern in natural_patterns:
            assert next_dates(natural_pattern, base_date) == expected_date


def test_invalid_repetition():
    """Invalid repetition."""
    assert next_dates(None, datetime.now()) is None
    assert next_dates('something really strange', datetime.now()) is None


def test_invalid_count():
    """Invalid count."""
    reference = datetime(1938, 8, 2)
    assert next_dates('daily', reference, 0) == datetime(1938, 8, 3)
    assert next_dates('daily', reference, -1) == datetime(1938, 8, 3)


def test_daily():
    """Daily repetitions."""
    reference = datetime(1938, 8, 2)
    assert next_dates('daily', reference) == datetime(1938, 8, 3)

    reference = datetime(1943, 5, 23)
    assert next_dates('Daily', reference) == datetime(1943, 5, 24)

    assert next_dates('Daily', reference, 1) == datetime(1943, 5, 24)
    assert next_dates('Daily', reference, 3) == [datetime(1943, 5, 24), datetime(1943, 5, 25), datetime(1943, 5, 26)]

    assert next_dates('every 2 days', datetime(1910, 9, 26), 3) == [
        datetime(1910, 9, 28), datetime(1910, 9, 30), datetime(1910, 10, 2)]


def test_weekly():
    """Weekly repetitions."""
    reference = datetime(1975, 8, 29)
    for pattern in ('weekly', 'every 1 week', 'every week', 'each week'):
        assert next_dates(pattern, reference, 2) == [datetime(1975, 9, 5), datetime(1975, 9, 12)]

    for pattern in ('biweekly', 'every 2 weeks', 'each 2 weeks'):
        assert next_dates(pattern, reference) == datetime(1975, 9, 12)


def test_monthly():
    """Monthly repetitions."""
    reference = datetime(1948, 3, 7, 6, 6, 6)
    for pattern in ('monthly', 'every 1 month', 'every month', 'each month'):
        assert next_dates(pattern, reference, 2) == [datetime(1948, 4, 7, 6, 6, 6), datetime(1948, 5, 7, 6, 6, 6)]

    for pattern in ('Bimonthly', 'every 2 MONTHS', 'each 2 monthS'):
        assert next_dates(pattern, reference) == datetime(1948, 5, 7, 6, 6, 6)

    for pattern in ('Quarterly', 'every 4 MONTHS', 'each 4 monthS'):
        assert next_dates(pattern, reference) == datetime(1948, 7, 7, 6, 6, 6)

    for pattern in ('Semiannually', 'every 6 MONTHS', 'each 6 monthS'):
        assert next_dates(pattern, reference) == datetime(1948, 9, 7, 6, 6, 6)


def test_yearly():
    """Yearly repetitions."""
    reference = datetime(1979, 8, 21, 3, 3, 3)
    for pattern in ('yearly', 'EVERY1YEAR', 'Each1Year', 'every 12 MONTHS', 'each 12 monthS'):
        assert next_dates(pattern, reference) == datetime(1980, 8, 21, 3, 3, 3)


def test_hourly():
    """Hourly repetitions."""
    reference = datetime(1969, 7, 9, 3, 22)
    for pattern in ('hourly', 'EVERY1hour', 'Each1hours'):
        assert next_dates(pattern, reference, 3) == [
            datetime(1969, 7, 9, 4, 22), datetime(1969, 7, 9, 5, 22), datetime(1969, 7, 9, 6, 22)]
