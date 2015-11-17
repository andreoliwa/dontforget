# -*- coding: utf-8 -*-
"""Repetition patterns for chores."""
from datetime import timedelta


class Every(object):
    """Base class for all repetition patterns."""

    def __init__(self, days=None):
        """Create instance.

        :param int days: Number of days for this repetition.
        """
        self.days = days

    def next_date(self, reference_date, count=1):
        """Return the next date(s) for this repetition.

        :param datetime.datetime|None reference_date: A datetime object.
        :param count: Number of next dates to return (default is 1).
        :return: Next date or a list of dates (if more than one).
        """
        if not reference_date:
            return None

        next_date_time = reference_date

        def calculate_next():
            """Calculate the next date time."""
            nonlocal next_date_time
            next_date_time = next_date_time + timedelta(days=self.days)
            return next_date_time

        dates_list = [calculate_next() for _ in range(count)]
        return dates_list if len(dates_list) > 1 else dates_list[0]


class Daily(Every):
    """Daily repetition."""

    def __init__(self, days=1):
        """Create instance.

        :param int days: Number of days for this repetition (default 1).
        """
        super(Daily, self).__init__(days=days)
