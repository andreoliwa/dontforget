# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
"""Tests for the repetition module."""
from datetime import datetime

from dontforget.repetition import next_dates


def test_simple_patterns_with_every_each():
    """Test simple repetition patterns using "every" and "each"."""
    base_date = datetime(1980, 9, 20, 8, 8, 8)
    mapping = {
        'Each 1 day': datetime(1980, 9, 21, 8, 8, 8),
        'Every 3 days': datetime(1980, 9, 23, 8, 8, 8),
        'Every 1 month': datetime(1980, 10, 20, 8, 8, 8),
        'Each 2 months': datetime(1980, 11, 20, 8, 8, 8),
        'Every 2 years': datetime(1982, 9, 20, 8, 8, 8),
        'EACH 6 WEEKS': datetime(1980, 11, 1, 8, 8, 8),
        'Every 1 hour': datetime(1980, 9, 20, 9, 8, 8),
        'every 15 minute': datetime(1980, 9, 20, 8, 23, 8)
    }
    for natural_pattern, expected_date in mapping.items():
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
    """Daily repetition possibilities."""
    reference = datetime(1938, 8, 2)
    assert next_dates('daily', reference) == datetime(1938, 8, 3)

    reference = datetime(1943, 5, 23)
    assert next_dates('Daily', reference) == datetime(1943, 5, 24)

    assert next_dates('Daily', reference, 1) == datetime(1943, 5, 24)
    assert next_dates('Daily', reference, 3) == [datetime(1943, 5, 24), datetime(1943, 5, 25), datetime(1943, 5, 26)]

    assert next_dates('every 2 days', datetime(1910, 9, 26), 3) == [
        datetime(1910, 9, 28), datetime(1910, 9, 30), datetime(1910, 10, 2)]
