# -*- coding: utf-8 -*-
"""User interface."""
from collections import namedtuple
from importlib import import_module

DialogResult = namedtuple('DialogResult', ('button', 'repetition'))


class DialogButton(object):
    """Available dialog buttons."""

    SNOOZE = 'Snooze'
    SKIP = 'Skip'
    COMPLETE = 'Complete'
    TIMEOUT = 'timeout'
    STOP = 'Stop'


def show_dialog(alarm, **kwargs):
    """Show a dialog for an alarm, using the module name that was specified in settings."""
    from dontforget.settings import UI_MODULE_NAME
    module = import_module('.{0}'.format(UI_MODULE_NAME), __name__)

    dialog_result = module.show_dialog(alarm, **kwargs)
    """:type: DialogResult"""
    if dialog_result is None:
        return

    method_mapping = {
        DialogButton.SNOOZE: alarm.snooze,
        DialogButton.SKIP: alarm.skip,
        DialogButton.COMPLETE: alarm.complete,
    }
    method = method_mapping.get(dialog_result.button)
    if method:
        if dialog_result.button == DialogButton.SNOOZE:
            method(dialog_result.repetition)
        else:
            method()

    return dialog_result
