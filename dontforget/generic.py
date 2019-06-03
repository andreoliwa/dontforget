# -*- coding: utf-8 -*-
"""Generic functions and classes, to be reused."""
import collections
from typing import Any, Dict, List, Union

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

    def __init__(self, *args, **kwargs):
        if not self._allow_creation:
            raise RuntimeError(
                f"You cannot create an instance of {self.__class__.__name__} directly. Use singleton() instead"
            )

    @classmethod
    def singleton(cls, *args, **kwargs):
        """Get a single instance of this class."""
        if not cls._instance:
            cls._allow_creation = True
            cls._instance = cls(*args, **kwargs)
            cls._allow_creation = False
        return cls._instance


def get_subclasses(cls):
    """Recursively get subclasses of a parent class."""
    subclasses = []
    for subclass in cls.__subclasses__():
        subclasses.append(subclass)
        subclasses += get_subclasses(subclass)
    return subclasses


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


def find_partial_keys(
    list_or_dict: Union[List[str], Dict[str, Any]], partial_key: str, not_found: str = None, multiple: str = None
) -> List[Union[str, Any]]:
    """Find a partial string on a list of strings or on a dict with string keys.

    >>> my_list = ["some", "strings", "here"]
    >>> find_partial_keys(my_list, "tri")
    ['strings']
    >>> find_partial_keys(my_list, "s")
    ['some', 'strings']
    >>> find_partial_keys(my_list, "x")
    []
    >>> find_partial_keys(my_list, "x", not_found="Not found!")
    Traceback (most recent call last):
     ...
    LookupError: Not found!
    >>> find_partial_keys(my_list, "x", not_found="No keys named {!r}!")
    Traceback (most recent call last):
     ...
    LookupError: No keys named 'x'!
    >>> find_partial_keys(my_list, "e", multiple="Multiple matches!")
    Traceback (most recent call last):
     ...
    LookupError: Multiple matches!
    >>> find_partial_keys(my_list, "e", multiple="Multiple matches: {}")
    Traceback (most recent call last):
     ...
    LookupError: Multiple matches: some, here

    >>> my_dict = {"some": 1, "strings": "2", "here": 3}
    >>> find_partial_keys({"some": 1, "strings": 2, "here": 3}, "tri")
    [2]
    >>> find_partial_keys(my_dict, "s")
    [1, '2']
    >>> find_partial_keys(my_dict, "x")
    []
    >>> find_partial_keys(my_dict, "x", not_found="Not found!")
    Traceback (most recent call last):
     ...
    LookupError: Not found!
    >>> find_partial_keys(my_dict, "x", not_found="No keys named {}!")
    Traceback (most recent call last):
     ...
    LookupError: No keys named x!
    >>> find_partial_keys(my_dict, "e", multiple="Multiple matches!")
    Traceback (most recent call last):
     ...
    LookupError: Multiple matches!
    >>> find_partial_keys(my_dict, "e", multiple="Multiple matches: {}")
    Traceback (most recent call last):
     ...
    LookupError: Multiple matches: some, here
    """
    if isinstance(list_or_dict, dict):
        found_objects = {key: obj for key, obj in list_or_dict.items() if partial_key.casefold() in key.casefold()}
        result = list(found_objects.values())
        found_keys = list(found_objects.keys())
    else:
        found_keys = [key for key in list_or_dict if partial_key.casefold() in key.casefold()]
        result = found_keys

    if not_found and not result:
        raise LookupError(not_found.format(partial_key))
    if multiple and len(result) > 1:
        raise LookupError(multiple.format(", ".join(found_keys)))
    return result


def pretty_plugin_name(class_) -> str:
    """Return a prettier name for the plugin, without the autogenerated namespace."""
    last_part = class_.__module__.split(".")[-1]
    return f"{last_part}.{class_.__name__}"
