# -*- encoding: utf-8 -*-
"""Tests for the main module."""
from dontforget.__main__ import main
from dontforget import Task, Daily, Every
from datetime import datetime


def test_main():
    """Main CLI function."""
    assert main([]) == 0


def test_task():
    """Task."""
    t = Task('Some name')
    assert t.name == 'Some name'
    assert t.description is None

    t = Task(description='Some text', name='Another')
    assert t.name == 'Another'
    assert t.description == 'Some text'


def test_daily():
    """Daily recurrence possibilities."""
    d = Daily()
    assert d.next() is None
    d.dt = datetime(1938, 8, 2)
    assert d.next() == datetime(1938, 8, 3)

    d = Daily(datetime(1943, 5, 23))
    e = Every(days=1, dt=datetime(1943, 5, 23))

    assert d.dt == datetime(1943, 5, 23)
    assert d.next() == datetime(1943, 5, 24)
    assert e.next() == d.next()

    assert d.next(1) == datetime(1943, 5, 24)
    assert d.next(3) == [datetime(1943, 5, 24), datetime(1943, 5, 25), datetime(1943, 5, 26)]

    d = Daily(datetime(1910, 9, 26), 2)
    assert d.next(3) == [datetime(1910, 9, 28), datetime(1910, 9, 30), datetime(1910, 10, 2)]


# TODO
# def test_due_date():
#     t = Task('Some task')
#     t.due_date('2015-03-15 23:30', Daily())
#     t.reminder('2015-03-15 08:30')
#     t.reminder('2015-03-15 15:30', Hourly())
#     t.reminder('2015-03-15 20:30', Every(minutes=15))
