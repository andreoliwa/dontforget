# -*- encoding: utf-8 -*-
"""Main module."""
from datetime import timedelta

__version__ = '0.1.0'


class Task(object):
    """A task."""

    def __init__(self, name, description=None):
        """Init object.

        :param name: Task name.
        :param description: Task description.
        :return:
        """
        self.name = name
        self.description = description


class Every(object):
    """Base class for all recurrence patterns."""

    def __init__(self, date_time=None, days=None):
        """Init object.

        :param date_time: A datetime object.
        :param days: Number of days for this recurrence.
        :return:
        """
        self._next_date_time = None
        self.date_time = date_time
        self.days = days

    def next_date(self, count=1):
        """Return the next date(s) for this recurrence.

        :param count: Number of next dates to return (default is 1).
        :return: Next date or a list of dates (if more than one).
        """
        if not self.date_time:
            return None

        self._next_date_time = self.date_time

        def calculate_next():
            """Calculate the next date time."""
            self._next_date_time = self._next_date_time + timedelta(days=self.days)
            return self._next_date_time

        dates_list = [calculate_next() for _ in range(count)]
        return dates_list if len(dates_list) > 1 else dates_list[0]


class Daily(Every):
    """Daily recurrence."""

    def __init__(self, dt=None, days=1):
        """Init object.

        :param dt: A datetime object.
        :param days: Number of days for this recurrence.
        :return:
        """
        super(Daily, self).__init__(dt, days)
