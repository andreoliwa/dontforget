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
