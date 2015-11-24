# -*- coding: utf-8 -*-
"""Repetition patterns for chores."""
import re

from dateutil.relativedelta import relativedelta

REGEX_EVERY = re.compile(r"""(?P<every>Every|Each)\s+(?P<number>\d+)\s+(?P<unit>.+)s?""", re.IGNORECASE)


def normalise_unit(value):
    """Normalise a unit (day, month, year...) to conform to dateutil naming (mainly making it a plural word)."""
    return value.lower().rstrip('s') + 's'


def every(reference_date, count, number, unit):
    """Add a number of units to a reference date."""
    if not count or int(count) <= 0:
        count = 1

    temp_date = reference_date
    results = []
    for dummy in range(count):
        temp_date = temp_date + relativedelta(**{normalise_unit(unit): int(number)})
        results.append(temp_date)
    return results if len(results) > 1 else results[0]


def next_dates(natural_language_repetition, reference_date, count=1):
    """Return the next date(s) by parsing a natural language repetition string.

    :param str natural_language_repetition: A string like 'daily', 'every 3 days', 'once a month', etc.
    :param datetime.datetime|None reference_date: A datetime object.
    :param count: Number of next dates to return (default is 1).
    :return: A repetition class that inherits from Every, or None if a class could not be matched.
    :rtype: None|Every|Daily
    """
    if not natural_language_repetition:
        return None

    if natural_language_repetition.lower() == 'daily':
        return every(reference_date, count, 1, 'day')

    match = REGEX_EVERY.match(natural_language_repetition)
    if match:
        match_dict = match.groupdict()
        match_dict.pop('every')
        return every(reference_date, count, **match_dict)

    return None
