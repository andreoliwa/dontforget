# pylint: disable=invalid-name,no-member
"""Test chores."""
from datetime import timedelta

import arrow
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


def test_create_alarms_for_active_chores(app):
    """Create alarms for active chores."""
    assert app

    veggie = ChoreFactory(title='Buy vegetables', alarm_start=YESTERDAY, alarm_end=YESTERDAY)
    coffee = ChoreFactory(title='Buy coffee', alarm_start=YESTERDAY, alarm_end=NEXT_WEEK)
    chocolate = ChoreFactory(title='Buy chocolate', alarm_start=YESTERDAY)
    db.session.commit()

    assert spawn_alarms() == 2
    db.session.commit()

    # No alarms for inactive chores, one alarm each for each active chore.
    assert len(veggie.alarms) == 0

    assert len(coffee.alarms) == 1
    alarm = coffee.alarms[0]
    assert alarm.next_at == coffee.alarm_start
    assert alarm.current_state == AlarmAction.UNSEEN

    assert len(chocolate.alarms) == 1
    alarm = chocolate.alarms[0]
    assert alarm.next_at == chocolate.alarm_start
    assert alarm.current_state == AlarmAction.UNSEEN

    # There should be one new alarm for chocolate.
    assert len(veggie.alarms) == 0
    assert len(coffee.alarms) == 1
    assert len(chocolate.alarms) == 1
    assert chocolate.alarms[0].next_at == chocolate.alarm_start
    assert chocolate.alarms[0].current_state == AlarmAction.UNSEEN

    # Nothing changed, so no spawn for you.
    assert spawn_alarms() == 0


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

        self.original_due_at = self.original_alarm_at = None
        self.reset_original()

    def reset_original(self):
        """Reset original dates."""
        self.original_due_at = self.chore.due_at
        self.original_alarm_at = self.chore.alarm_at

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
        # assert last_alarm.due_at == self.original_due_at
        # assert last_alarm.alarm_at == self.original_alarm_at

    def assert_timedelta(self, **kwargs):
        """Assert if the due and alarm times match the timedelta."""
        expected_due_at = expected_alarm_at = None
        if kwargs:
            diff = timedelta(**kwargs)
            expected_due_at = self.original_due_at + diff
            expected_alarm_at = self.original_alarm_at + diff
        assert self.chore.due_at == expected_due_at
        assert self.chore.alarm_at == expected_alarm_at

        self.reset_original()

    def assert_close_to_now(self, seconds: int=2, **kwargs):
        """Assert both chore dates are close to the current time (since we cannot assert the exact time)."""
        expected_at = right_now()
        if kwargs:
            expected_at += timedelta(**kwargs)

        begin = expected_at - timedelta(seconds=seconds)
        end = expected_at + timedelta(seconds=seconds)
        assert begin <= self.chore.due_at <= end
        assert begin <= self.chore.alarm_at <= end

        self.reset_original()


def test_one_time_only(app):
    """One time only chore."""
    fake = FakeChore(app)

    fake.chore.complete()
    fake.assert_timedelta()
    fake.assert_saved_alarm(1, AlarmAction.COMPLETE)


def test_repetition_from_due_date(app):
    """Chore with repetition from due date."""
    fake = FakeChore(app, repetition='Daily')

    fake.chore.complete()
    fake.assert_timedelta(days=1)
    fake.assert_saved_alarm(1, AlarmAction.COMPLETE)

    fake.chore.complete()
    fake.assert_timedelta(days=1)
    fake.assert_saved_alarm(2, AlarmAction.COMPLETE)

    fake.chore.finish()
    fake.assert_timedelta(days=1)
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


def test_snooze_from_original_due_date(app):
    """When you snooze a chore and then complete it later, the original date should get the repetition."""
    assert app

    ten_oclock = TODAY.replace(hour=10, minute=0, second=0, microsecond=0)
    chore = ChoreFactory(repetition='Daily', repeat_from_completed=False)
    AlarmFactory(chore=chore, next_at=ten_oclock)
    """:type: dontforget.models.Alarm"""
    db.session.commit()

    def get_last_alarm(expected_len):
        """Get the last alarm from the chore.

        :rtype: dontforget.models.Alarm
        """
        assert len(chore.alarms) == expected_len
        return chore.alarms[expected_len - 1]

    last_alarm = get_last_alarm(1)
    assert last_alarm.next_at == ten_oclock

    # Snooze several times.
    for index, minutes in enumerate([2, 1, 4]):
        last_alarm.snooze('{} hours'.format(minutes))
        last_alarm = get_last_alarm(2 + index)

    # Skip one day.
    last_alarm.skip()
    last_alarm = get_last_alarm(5)
    assert last_alarm.next_at == ten_oclock + timedelta(days=1)

    # Snooze again several times.
    for index, minutes in enumerate([10, 15, 30, 10]):
        last_alarm.snooze('{} minutes'.format(minutes))
        last_alarm = get_last_alarm(6 + index)

    # Finally complete the chore the next day.
    last_alarm.complete()
    last_alarm = get_last_alarm(10)
    assert last_alarm.next_at == ten_oclock + timedelta(days=2)


def test_spawn_alarm_for_future_chores(app):
    """Spawn alarms for future chores."""
    assert app

    next_week = arrow.utcnow().shift(weeks=1).datetime
    ChoreFactory(title='Start a diet', alarm_start=next_week)
    db.session.commit()

    assert spawn_alarms() == 1
    assert Alarm.query.first().next_at == next_week
