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


def show_dialog(alarm):
    """Show a dialog for an alarm, using the module name that was specified in settings."""
    from dontforget.settings import UI_MODULE_NAME
    module = import_module('.{0}'.format(UI_MODULE_NAME), __name__)

    dialog_result = module.show_dialog(alarm)
    """:type: DialogResult"""

    method_mapping = {
        DialogButton.COMPLETE: alarm.complete,
        DialogButton.SKIP: alarm.skip
    }
    change_alarm = method_mapping.get(dialog_result.button)
    if change_alarm:
        change_alarm()

    return dialog_result
