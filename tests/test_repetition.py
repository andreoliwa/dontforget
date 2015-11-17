# -*- coding: utf-8 -*-
"""Tests for the repetition module."""
from datetime import datetime

from dontforget.repetition import Daily, Every


def test_daily():
    """Daily repetition possibilities."""
    daily = Daily()
    assert daily.next_date(None) is None
    assert daily.next_date(datetime(1938, 8, 2)) == datetime(1938, 8, 3)

    daily = Daily()
    every = Every(days=1)

    reference = datetime(1943, 5, 23)
    assert daily.next_date(reference) == every.next_date(reference) == datetime(1943, 5, 24)

    assert daily.next_date(reference, 1) == datetime(1943, 5, 24)
    assert daily.next_date(reference, 3) == [datetime(1943, 5, 24), datetime(1943, 5, 25), datetime(1943, 5, 26)]

    daily = Daily(2)
    assert daily.next_date(datetime(1910, 9, 26), 3) == [
        datetime(1910, 9, 28), datetime(1910, 9, 30), datetime(1910, 10, 2)]

# TODO
# def test_due_date():
#     t = Chore('Do something')
#     t.due_date('2015-03-15 23:30', Daily())
#     t.reminder('2015-03-15 08:30')
#     t.reminder('2015-03-15 15:30', Hourly())
#     t.reminder('2015-03-15 20:30', Every(minutes=15))
