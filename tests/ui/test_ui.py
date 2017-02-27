"""Test user interface."""
# pylint: disable=invalid-name,no-member,too-many-arguments
from unittest.mock import call, patch

import pytest

from dontforget.cron import display_unseen_alarms
from dontforget.extensions import db
from dontforget.models import AlarmState
from dontforget.ui import DialogButton, DialogResult
from tests.factories import NEXT_WEEK, TODAY, YESTERDAY, AlarmFactory


@patch('dontforget.ui.show_dialog')
def test_display_windows_for_unseen_alarms(mocked_dialog, app):
    """Display a window for every chore with an unseen alarm before right now."""
    assert app

    # Create some alarms
    due_alarms = [AlarmFactory() for _ in range(5)]
    future_alarms = [AlarmFactory(next_at=NEXT_WEEK) for _ in range(2)]
    db.session.commit()

    for alarm in due_alarms + future_alarms:
        assert alarm.current_state == AlarmState.UNSEEN

    # Display notification windows for all unseen alarms
    assert display_unseen_alarms() == 5
    assert mocked_dialog.call_count == 5
    mocked_dialog.assert_has_calls([call(alarm) for alarm in due_alarms])

    # Change the alarm state to displayed right after displaying a window
    for alarm in due_alarms:
        assert alarm.current_state == AlarmState.DISPLAYED
    for alarm in future_alarms:
        assert alarm.current_state == AlarmState.UNSEEN


@patch('subprocess.check_output', return_value=b'Snooze\n15 minutes\n')
@patch('dontforget.settings.UI_MODULE_NAME', return_value='cocoa_dialog')
def test_valid_module(mocked_module_name, mocked_check_output, app):
    """Test a valid module name."""
    assert app
    assert mocked_check_output

    alarm = AlarmFactory()
    db.session.commit()
    assert alarm.current_state == AlarmState.UNSEEN

    mocked_module_name.__str__.return_value = mocked_module_name.return_value
    assert display_unseen_alarms() == 1


def assert_state(mocked_dialog, expected_call_count, db_, alarm_dict, expected_states, expected_unseen_alarms=1):
    """Assert alarm(s) were created with the expected state(s).

    :param mocked_dialog: A mocked dialog window that simulates a clicked button.
    :param expected_call_count: How many times the fake dialog is supposed to be shown.
    :param db_: Database.
    :param alarm_dict: Fields to be used with the alarm factory.
    :param list|str expected_states: A list or a single expected state for the alarms, after displaying them.
    :param int expected_unseen_alarms: Expected quantity of unseen alarms.
    :return: List of created alarms.
    """
    alarm = AlarmFactory(**alarm_dict)
    db_.session.commit()
    assert alarm.current_state == AlarmState.UNSEEN

    assert display_unseen_alarms() == expected_unseen_alarms
    assert mocked_dialog.call_count == expected_call_count
    mocked_dialog.assert_called_with(alarm)

    if not isinstance(expected_states, list):
        expected_states = [expected_states]
    assert len(alarm.chore.alarms) == len(expected_states)
    for index, expected_state in enumerate(expected_states):
        assert alarm.chore.alarms[index].current_state == expected_state
    return alarm.chore.alarms


@patch('dontforget.ui.cocoa_dialog.show_dialog')
def test_dialog_is_shown(mocked_dialog, app):
    """Test if a dialog is shown for an alarm."""
    assert app
    assert_state(mocked_dialog, 1, db, dict(), AlarmState.DISPLAYED)


@patch('dontforget.settings.UI_MODULE_NAME', return_value='some_non_existent_module')
def test_invalid_module(mocked_module_name, app):
    """Test an invalid module name."""
    assert app
    alarm = AlarmFactory()
    db.session.commit()
    assert alarm.current_state == AlarmState.UNSEEN

    mocked_module_name.__str__.return_value = mocked_module_name.return_value
    with pytest.raises(ImportError):
        display_unseen_alarms()


@patch('dontforget.ui.cocoa_dialog.show_dialog', return_value=DialogResult(DialogButton.COMPLETE, ''))
def test_alarm_completed(mocked_dialog, app):
    """Complete chores."""
    assert app
    assert_state(mocked_dialog, 1, db, dict(chore__repetition=None), AlarmState.COMPLETED)
    assert_state(mocked_dialog, 2, db, dict(chore__repetition='Daily', chore__alarm_end=YESTERDAY),
                 AlarmState.COMPLETED)
    assert_state(mocked_dialog, 3, db, dict(chore__repetition='Daily'), [AlarmState.COMPLETED, AlarmState.UNSEEN])


@patch('dontforget.ui.cocoa_dialog.show_dialog', return_value=DialogResult(DialogButton.SKIP, ''))
def test_alarm_skipped(mocked_dialog, app):
    """Skip chores."""
    assert app
    assert_state(mocked_dialog, 1, db, dict(chore__repetition=None), AlarmState.SKIPPED)
    assert_state(mocked_dialog, 2, db, dict(chore__repetition='Daily', chore__alarm_end=YESTERDAY),
                 AlarmState.SKIPPED)
    assert_state(mocked_dialog, 3, db, dict(chore__repetition='Daily'), [AlarmState.SKIPPED, AlarmState.UNSEEN])


@patch('dontforget.ui.cocoa_dialog.show_dialog', return_value=DialogResult(DialogButton.SNOOZE, '28 days'))
def test_alarm_snoozed(mocked_dialog, app):
    """Snooze chores: repetition doesn't matter, new alarms are always spawned."""
    assert app
    expected = [AlarmState.SNOOZED, AlarmState.UNSEEN]
    alarms = assert_state(mocked_dialog, 1, db, dict(chore__repetition=None), expected)
    assert (alarms[1].next_at - TODAY).days == 28

    alarms = assert_state(mocked_dialog, 2, db, dict(chore__repetition='Daily', chore__alarm_end=YESTERDAY), expected)
    assert (alarms[1].next_at - TODAY).days == 28

    alarms = assert_state(mocked_dialog, 3, db, dict(chore__repetition='Daily'), expected)
    assert (alarms[1].next_at - TODAY).days == 28


@patch('dontforget.ui.cocoa_dialog.show_dialog', return_value=DialogResult(DialogButton.TIMEOUT, ''))
def test_alarm_timeout(mocked_dialog, app):
    """Reset alarm on timeout."""
    assert app
    assert_state(mocked_dialog, 1, db, dict(chore__repetition=None), AlarmState.UNSEEN)

    mocked_dialog.reset_mock()
    assert_state(mocked_dialog, 2, db, dict(chore__repetition='Daily', chore__alarm_end=YESTERDAY),
                 AlarmState.UNSEEN, expected_unseen_alarms=2)

    mocked_dialog.reset_mock()
    assert_state(mocked_dialog, 3, db, dict(chore__repetition='Daily'), AlarmState.UNSEEN,
                 expected_unseen_alarms=3)


@patch('dontforget.ui.cocoa_dialog.show_dialog', return_value=DialogResult(DialogButton.SNOOZE, '8 years'))
def test_last_snooze(mocked_dialog, app):
    """Suggest snooze times for the next alarm."""
    assert app
    alarms = assert_state(mocked_dialog, 1, db, dict(), [AlarmState.SNOOZED, AlarmState.UNSEEN])
    assert alarms[1].last_snooze == '8 years'
