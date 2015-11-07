# -*- encoding: utf-8 -*-
"""Tests for the main module."""
from datetime import datetime

from dontforget.models import Daily, Every, Task


def test_task():
    """Task."""
    task = Task('Some name')
    assert task.name == 'Some name'
    assert task.description is None

    task = Task(description='Some text', name='Another')
    assert task.name == 'Another'
    assert task.description == 'Some text'


def test_daily():
    """Daily recurrence possibilities."""
    daily = Daily()
    assert daily.next_date() is None
    daily.date_time = datetime(1938, 8, 2)
    assert daily.next_date() == datetime(1938, 8, 3)

    daily = Daily(datetime(1943, 5, 23))
    every = Every(days=1, date_time=datetime(1943, 5, 23))

    assert daily.date_time == datetime(1943, 5, 23)
    assert daily.next_date() == datetime(1943, 5, 24)
    assert every.next_date() == daily.next_date()

    assert daily.next_date(1) == datetime(1943, 5, 24)
    assert daily.next_date(3) == [datetime(1943, 5, 24), datetime(1943, 5, 25), datetime(1943, 5, 26)]

    daily = Daily(datetime(1910, 9, 26), 2)
    assert daily.next_date(3) == [datetime(1910, 9, 28), datetime(1910, 9, 30), datetime(1910, 10, 2)]

# TODO
# def test_due_date():
#     t = Task('Some task')
#     t.due_date('2015-03-15 23:30', Daily())
#     t.reminder('2015-03-15 08:30')
#     t.reminder('2015-03-15 15:30', Hourly())
#     t.reminder('2015-03-15 20:30', Every(minutes=15))
