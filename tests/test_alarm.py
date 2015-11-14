# -*- coding: utf-8 -*-
# pylint: disable=invalid-name,no-member
"""Tests the alarm model."""
from unittest.mock import call, patch

from dontforget.cron import display_unseen_alarms
from dontforget.models import AlarmState
from tests.factories import AlarmFactory


@patch('dontforget.ui.show_dialog')
def test_display_windows_for_unseen_alarms(mocked_dialog, db):
    """Display a window for every chore with an unseen alarm."""
    # Create some alarms
    alarms = [AlarmFactory() for dummy in range(5)]
    db.session.commit()

    for alarm in alarms:
        assert alarm.current_state == AlarmState.UNSEEN

    # Display notification windows for all unseen alarms
    assert display_unseen_alarms() == 5
    assert mocked_dialog.call_count == 5
    mocked_dialog.assert_has_calls([call(alarm) for alarm in alarms])

    # Change the alarm state to displayed right after displaying a window
    for alarm in alarms:
        assert alarm.current_state == AlarmState.DISPLAYED
