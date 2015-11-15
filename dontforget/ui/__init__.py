# -*- coding: utf-8 -*-
"""User interface."""
from importlib import import_module


def show_dialog(alarm):
    """Show a dialog for an alarm, using the module name that was specified in settings."""
    from dontforget.settings import UI_MODULE_NAME
    module = import_module('.{0}'.format(UI_MODULE_NAME), __name__)
    return module.show_dialog(alarm)
