# -*- coding: utf-8 -*-
"""Helper utilities and decorators."""
from flask import flash

DATETIME_FORMAT = "ddd DD/MM HH:mm"


class UT:
    """Unicode table helper.

    Helpful links:
    - https://unicode-table.com/en/
    - http://apps.timwhitlock.info/unicode/inspect
    """

    AnticlockwiseOpenCircleArrow = "\u21ba"
    Cyclone = "\U0001F300"
    DoubleExclamationMark = "\u203C\uFE0F"
    EmptySet = "\u2205"
    ExclamationQuestionMark = "\u2049\uFE0F"
    Fire = "\U0001F525"
    FourLeafClover = "\U0001F340"
    WhiteHeavyCheckMark = "\u2705"
    GreenHeart = "\U0001F49A"
    HeavyExclamationMarkSymbol = "\u2757"
    Hourglass = "\u231b"
    LargeBlueCircle = "\U0001F535"
    LargeRedCircle = "\U0001F534"
    MediumWhiteCircle = "\u26AA"
    WarningSign = "\u26A0"
    WhiteExclamationMarkOrnament = "\u2755"
    WhiteQuestionMarkOrnament = "\u2754"


def flash_errors(form, category="warning"):
    """Flash all errors for a form."""
    for field, errors in form.errors.items():
        for error in errors:
            flash("{0} - {1}".format(getattr(form, field).label.text, error), category)
