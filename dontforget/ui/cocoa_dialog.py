# -*- coding: utf-8 -*-
"""Cocoa dialog window for MacOS."""
from subprocess import CalledProcessError, check_output

from dontforget.settings import COCOA_DIALOG_PATH
from dontforget.ui import DialogButton, DialogResult


def show_dialog(alarm):
    """Show a dialog for an alarm using the Cocoa Dialog app.

    :param dontforget.models.Alarm alarm: The alarm to show.
    :return: A named tuple with the button and repetition that were selected.
    """
    if not COCOA_DIALOG_PATH:
        raise RuntimeError('Cocoa Dialog path is not configured')
    repetition_items = ['5 minutes', '10 minutes', '15 minutes', 'Half an hour', '1 hour', '2 hours', '4 hours',
                        '12 hours', '1 day']  # TODO: This is only an example
    args = [COCOA_DIALOG_PATH, 'dropdown', '--string-output',
            '--title', alarm.chore.title,
            '--text', 'Snooze this alarm for:',
            '--icon', 'finder',
            '--button1', DialogButton.SNOOZE,
            '--button3', DialogButton.COMPLETE]
    if alarm.chore.repetition and alarm.chore.active():
        # Only show the skip button for active chores with repetition.
        args.extend(['--button2', DialogButton.SKIP])

    args.extend(['--items'] + [item + ' (NOT WORKING YET)' for item in repetition_items])
    try:
        output = check_output(args)
    except CalledProcessError as err:
        output = err.output
    return DialogResult(*output.decode().splitlines())
