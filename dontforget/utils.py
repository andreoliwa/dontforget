# -*- coding: utf-8 -*-
"""Helper utilities and decorators."""
from flask import flash

DATETIME_FORMAT = 'ddd MMM DD, YYYY HH:mm'
TIMEZONE = 'Europe/Berlin'


class UT:
    """Unicode table helper."""

    LargeRedCircle = '\U0001F534'
    LargeBlueCircle = '\U0001F535'


def flash_errors(form, category='warning'):
    """Flash all errors for a form."""
    for field, errors in form.errors.items():
        for error in errors:
            flash('{0} - {1}'.format(getattr(form, field).label.text, error), category)


def to_list(value, default_when_none=None):
    """Cast a value to a list.

    `list(value)` doesn't work as expected if `value` is a string:
    it would return a list with every character as an element.

    :param value: Value to be cast to list.
    :param default_when_none: Return this default if value is none.

    :return: Value inside a list.
    :rtype: list
    """
    if value is None:
        return default_when_none
    return [value] if not isinstance(value, (list, tuple)) else value
