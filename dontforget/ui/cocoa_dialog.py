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
    args = [COCOA_DIALOG_PATH, 'inputbox', '--string-output',
            '--title', alarm.chore.title,
            '--text', '1 hour',
            '--informative-text', 'Snooze this alarm for:',
            '--icon', 'finder',
            '--button1', DialogButton.SNOOZE,
            '--button3', DialogButton.COMPLETE]
    if alarm.chore.repetition and alarm.chore.active():
        # Only show the skip button for active chores with repetition.
        args.extend(['--button2', DialogButton.SKIP])

    try:
        output = check_output(args)
    except CalledProcessError as err:
        output = err.output
    return DialogResult(*output.decode().splitlines())
