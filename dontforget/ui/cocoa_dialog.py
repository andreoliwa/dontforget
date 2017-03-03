# -*- coding: utf-8 -*-
"""Cocoa dialog window for MacOS."""
from subprocess import CalledProcessError, check_output

from dontforget.settings import UI_COCOA_DIALOG_PATH, UI_DEFAULT_SNOOZE
from dontforget.ui import DialogButton, DialogResult


def show_dialog(alarm):
    """Show a dialog for an alarm using the Cocoa Dialog app.

    :param dontforget.models.Alarm alarm: The alarm to show.
    :return: A named tuple with the button and repetition that were selected.
    """
    if not UI_COCOA_DIALOG_PATH:
        raise RuntimeError('Cocoa Dialog path is not configured')
    suggested_snooze = alarm.snooze_text if alarm.snooze_text else UI_DEFAULT_SNOOZE
    args = [UI_COCOA_DIALOG_PATH, 'inputbox', '--string-output',
            '--title', alarm.chore.title,
            '--text', suggested_snooze,
            '--informative-text', 'Snooze this alarm for:',
            '--icon', 'finder',
            # '--timeout', str(UI_DIALOG_TIMEOUT),
            '--button1', DialogButton.SNOOZE,
            '--button3', DialogButton.COMPLETE]
    if alarm.chore.repetition and alarm.chore.active():
        # Only show the skip button for active chores with repetition.
        args.extend(['--button2', DialogButton.SKIP])

    try:
        output = check_output(args)
    except CalledProcessError as err:
        output = err.output
    lines = output.decode().splitlines()
    if len(lines) == 1:
        # Append an empty string in case of timeout.
        lines.append('')
    return DialogResult(*lines)
