"""Repetition patterns for chores."""
import datetime
import re
from typing import Optional

import arrow
from dateutil.relativedelta import relativedelta

from dontforget.settings import LOCAL_TIMEZONE


class Unit(object):
    """Units of time used in repetitions."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    HOUR = "hour"
    MINUTE = "minute"


REGEX_EVERY = re.compile(r"""(?P<every>Every|Each)?\s*(?P<number>\d*)\s*(?P<unit>.+)s?""", re.IGNORECASE)
FREQUENCY_MAPPING = {
    "daily": (1, Unit.DAY),
    "weekly": (1, Unit.WEEK),
    "biweekly": (2, Unit.WEEK),
    "monthly": (1, Unit.MONTH),
    "bimonthly": (2, Unit.MONTH),
    "quarterly": (4, Unit.MONTH),
    "semiannually": (6, Unit.MONTH),
    "yearly": (1, Unit.YEAR),
    "hourly": (1, Unit.HOUR),
}

# Using 'm' for minute, because it's more likely to be used than 'month'
ABBREVIATIONS = {
    "d": Unit.DAY,
    "mo": Unit.MONTH,
    "y": Unit.YEAR,
    "w": Unit.WEEK,
    "h": Unit.HOUR,
    "m": Unit.MINUTE,
    "mi": Unit.MINUTE,
    "min": Unit.MINUTE,
}


def right_now(date=None) -> arrow.Arrow:
    """Current date/time in the UTC timezone, or the date passed as an argument.

    The reference date is returned as is, no checking.
    This function can be mocked on tests.
    """
    if date:
        return date if isinstance(date, arrow.Arrow) else arrow.get(date)
    return arrow.utcnow()


def local_right_now(date=None) -> arrow.Arrow:
    """Current datetime in the local timezone."""
    return right_now(date).to(LOCAL_TIMEZONE)


def normalise_unit(value):
    """Normalise a unit (day, month, year...) to conform to dateutil naming (mainly making it a plural word)."""
    clean = value.lower().rstrip("s")
    return ABBREVIATIONS.get(clean, clean) + "s"


def every(reference_date, count, number, unit):
    """Add a number of units to a reference date."""
    if not count or int(count) <= 0:
        count = 1
    if not number or int(number) <= 0:
        number = 1

    temp_date = reference_date
    results = []
    for _index in range(count):
        try:
            temp_date = temp_date + relativedelta(**{normalise_unit(unit): int(number)})
        except TypeError:
            return None
        results.append(temp_date)
    return results if len(results) > 1 else results[0]


def next_dates(natural_language_repetition, reference_date=None, count=1) -> Optional[datetime.datetime]:
    """Return the next date(s) by parsing a natural language repetition string.

    :param str natural_language_repetition: A string like 'daily', 'every 3 days', 'once a month', etc.
    :param datetime.datetime|None reference_date: A datetime object.
    :param count: Number of next dates to return (default is 1).
    :return: A repetition class that inherits from Every, or None if a class could not be matched.
    :rtype: None|Every|Daily
    """
    if not natural_language_repetition:
        return None
    if not reference_date:
        reference_date = right_now().datetime

    mapping = FREQUENCY_MAPPING.get(natural_language_repetition.lower())
    if mapping:
        return every(reference_date, count, mapping[0], mapping[1])

    match = REGEX_EVERY.match(natural_language_repetition)
    if match:
        match_dict = match.groupdict()
        match_dict.pop("every")
        return every(reference_date, count, **match_dict)

    return None
