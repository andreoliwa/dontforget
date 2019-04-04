# -*- coding: utf-8 -*-
"""Generic functions and classes, to be reused."""
import collections

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


class SingletonMixin:
    """Singleton mixin for classes."""

    _allow_creation = False
    _instance = None

    def __init__(self):
        if not self._allow_creation:
            raise RuntimeError(
                f"You cannot create an instance of {self.__class__.__name__} directly. Use get_singleton() instead"
            )

    @classmethod
    def get_singleton(cls):
        """Get a single instance of this class."""
        if not cls._instance:
            cls._allow_creation = True
            cls._instance = cls()
            cls._allow_creation = False
        return cls._instance


def flatten(dict_, parent_key="", separator="."):
    """Flatten a nested dict.

    Use :py:meth:`unflatten()` to revert.

    >>> flatten({"root": {"sub1": 1, "sub2": {"deep": 3}}, "sibling": False})
    {'root.sub1': 1, 'root.sub2.deep': 3, 'sibling': False}
    """
    items = []
    for key, value in dict_.items():
        new_key = parent_key + separator + key if parent_key else key
        if isinstance(value, collections.abc.MutableMapping):
            items.extend(flatten(value, new_key, separator=separator).items())
        else:
            items.append((new_key, value))
    return dict(items)


def unflatten(dict_, separator="."):
    """Turn back a flattened dict created by :py:meth:`flatten()` into a nested dict.

    >>> unflatten({"my.sub.path": True, "another.path": 3, "my.home": 4})
    {'my': {'sub': {'path': True}, 'home': 4}, 'another': {'path': 3}}
    """
    items = {}
    for key, value in dict_.items():
        keys = key.split(separator)
        sub_items = items
        for index in keys[:-1]:
            try:
                sub_items = sub_items[index]
            except KeyError:
                sub_items[index] = {}
                sub_items = sub_items[index]

        sub_items[keys[-1]] = value

    return items
