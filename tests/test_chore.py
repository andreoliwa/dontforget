# pylint: disable=invalid-name,no-member
"""Test chores."""
from datetime import timedelta

import arrow
import pytest
from tests.factories import NEXT_WEEK, TODAY, YESTERDAY, AlarmFactory, ChoreFactory

from dontforget.app import db
from dontforget.cron import spawn_alarms
from dontforget.models import Alarm, AlarmAction, Chore
from dontforget.repetition import right_now


def test_search_similar(app):
    """Search for similar chores."""
    assert app

    first = ChoreFactory(title='My first chore')
    something = ChoreFactory(title='Do SOMETHING soon')
    coffee = ChoreFactory(title='Buy coffee')
    cheese = ChoreFactory(title='Buy cheese')
    db.session.commit()
    assert len(Chore(title='Write anything').search_similar()) == 0

    rv = Chore(title='Read something now').search_similar()
    assert len(rv) == 1
    assert rv == [something]

    rv = Chore(title='Buy bread').search_similar()
    assert len(rv) == 2
    assert {coffee, cheese}.issubset(set(rv))

    assert len(Chore(title='Buy bread').search_similar(min_chars=4)) == 0
    assert len(Chore(title='My duty').search_similar()) == 0

    rv = Chore(title='My first duty').search_similar()
    assert len(rv) == 1
    assert rv == [first]


def test_active_inactive_chores(app):
    """Query active and inactive chores."""
    assert app

    ChoreFactory(due_at=YESTERDAY, alarm_end=YESTERDAY)
    ChoreFactory(due_at=YESTERDAY, alarm_end=NEXT_WEEK)
    ChoreFactory(due_at=YESTERDAY)
    db.session.commit()

    assert Chore.query_active().count() == 2
    assert Chore.query_inactive().count() == 1

    after_next_week = NEXT_WEEK + timedelta(seconds=1)
    assert Chore.query_active(after_next_week).count() == 1
    assert Chore.query_inactive(after_next_week).count() == 2


class FakeChore:
    """Helper to create and assert chores and alarms."""

    def __init__(self, app, **kwargs):
        """Init the helper."""
        assert app

        due_at = kwargs.pop('due_at', YESTERDAY)
        alarm_at = kwargs.pop('alarm_at', due_at)
        self.chore = ChoreFactory(due_at=due_at, alarm_at=alarm_at, **kwargs)
        """:type: Chore"""
        db.session.commit()

        self.previous_due_at = self.previous_alarm_at = None
        self.reset_previous_dates()

    def reset_previous_dates(self, reset_due=True, reset_alarm=True):
        """Reset previous dates."""
        if reset_due:
            self.previous_due_at = self.chore.due_at
        if reset_alarm:
            self.previous_alarm_at = self.chore.alarm_at

    def alarm(self, index):
        """Get an alarm from the underlying chore.

        :rtype: Alarm
        """
        return self.chore.alarms[index]

    def assert_saved_alarm(self, expected_alarm_count, expected_action):
        """Assert an alarm was saved to the history."""
        assert len(self.chore.alarms) == expected_alarm_count

        last_alarm = self.chore.alarms[expected_alarm_count - 1]
        """:type: Alarm"""
        assert last_alarm.action == expected_action
        # TODO Augusto:
        # assert last_alarm.due_at == self.previous_due_at
        # assert last_alarm.alarm_at == self.previous_alarm_at

    def assert_both_dates(self, **kwargs):
        """Assert if the due and alarm times match the timedelta."""
        expected_due_at = expected_alarm_at = None
        if kwargs:
            diff = timedelta(**kwargs)
            expected_due_at = self.previous_due_at + diff
            expected_alarm_at = self.previous_alarm_at + diff
        assert self.chore.due_at == expected_due_at
        assert self.chore.alarm_at == expected_alarm_at

        self.reset_previous_dates()

    def assert_alarm_at(self, **kwargs):
        """Assert if the alarm time match the timedelta."""
        expected_alarm_at = None
        if kwargs:
            diff = timedelta(**kwargs)
            expected_alarm_at = self.previous_alarm_at + diff

        assert self.chore.due_at == self.previous_due_at
        assert self.chore.alarm_at == expected_alarm_at, 'Expected {}, got {}'.format(
            arrow.get(expected_alarm_at).humanize(),
            arrow.get(self.chore.alarm_at).humanize(),
        )

        self.reset_previous_dates(reset_due=False)

    def assert_close_to_now(self, seconds: int=2, **kwargs):
        """Assert both chore dates are close to the current time (since we cannot assert the exact time)."""
        expected_at = right_now()
        if kwargs:
            expected_at += timedelta(**kwargs)

        begin = expected_at - timedelta(seconds=seconds)
        end = expected_at + timedelta(seconds=seconds)
        assert begin <= self.chore.due_at <= end
        assert begin <= self.chore.alarm_at <= end

        self.reset_previous_dates()


def test_one_time_only(app):
    """One time only chore."""
    fake = FakeChore(app)

    fake.chore.complete()
    fake.assert_both_dates()
    fake.assert_saved_alarm(1, AlarmAction.COMPLETE)


def test_repetition_from_due_date(app):
    """Chore with repetition from due date."""
    fake = FakeChore(app, repetition='Daily')

    fake.chore.complete()
    fake.assert_both_dates(days=1)
    fake.assert_saved_alarm(1, AlarmAction.COMPLETE)

    fake.chore.complete()
    fake.assert_both_dates(days=1)
    fake.assert_saved_alarm(2, AlarmAction.COMPLETE)

    fake.chore.finish()
    fake.assert_both_dates(days=1)
    fake.assert_saved_alarm(3, AlarmAction.FINISH)


def test_repetition_from_completed(app):
    """Chore with repetition from completion date."""
    fake = FakeChore(app, repetition='Every 2 days', due_at=YESTERDAY, repeat_from_completed=True)

    fake.chore.complete()
    fake.assert_close_to_now(days=2)
    fake.assert_saved_alarm(1, AlarmAction.COMPLETE)

    fake.chore.complete()
    fake.assert_close_to_now(days=2)
    fake.assert_saved_alarm(2, AlarmAction.COMPLETE)

    fake.chore.finish()
    fake.assert_close_to_now(days=2)
    fake.assert_saved_alarm(3, AlarmAction.FINISH)


@pytest.mark.xfail(reason='Fix this')
def test_snooze_from_original_due_date(app):
    """When you snooze a chore and then complete it later, the original date should get the repetition."""
    ten_oclock = TODAY.replace(hour=10, minute=0, second=0, microsecond=0)
    fake = FakeChore(app, repetition='Daily', due_at=ten_oclock)

    # Snooze several times.
    for index, hours in enumerate([2, 1, 4]):
        fake.chore.snooze('{} hours'.format(hours))
        fake.assert_alarm_at(minutes=hours)
    #
    # # Skip one day.
    # fake.chore.skip()
    # last_alarm = get_last_alarm(5)
    # assert last_alarm.next_at == ten_oclock + timedelta(days=1)
    #
    # # Snooze again several times.
    # for index, minutes in enumerate([10, 15, 30, 10]):
    #     last_alarm.snooze('{} minutes'.format(minutes))
    #     last_alarm = get_last_alarm(6 + index)
    #
    # # Finally complete the chore the next day.
    # last_alarm.complete()
    # last_alarm = get_last_alarm(10)
    # assert last_alarm.next_at == ten_oclock + timedelta(days=2)


@pytest.mark.xfail(reason='Fix this')
def test_spawn_alarm_for_future_chores(app):
    """Spawn alarms for future chores."""
    assert app

    next_week = arrow.utcnow().shift(weeks=1).datetime
    ChoreFactory(title='Start a diet', alarm_start=next_week)
    db.session.commit()

    assert spawn_alarms() == 1
    assert Alarm.query.first().next_at == next_week
