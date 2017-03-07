# pylint: disable=invalid-name,no-member
"""Test chores."""
from datetime import timedelta

import arrow
from tests.factories import NEXT_WEEK, TODAY, YESTERDAY, ChoreFactory

from dontforget.app import db
from dontforget.models import AlarmAction, Chore
from dontforget.repetition import right_now
from dontforget.utils import DATETIME_FORMAT


class FakeChore:
    """Helper to create and assert chores and alarms."""

    # Seconds to compare to the current date.
    NOW_PRECISION_SECONDS = 1

    def __init__(self, app, assert_alarm_dates=True, **kwargs):
        """Init the helper."""
        assert app

        due_at = kwargs.pop('due_at', YESTERDAY)
        alarm_at = kwargs.pop('alarm_at', due_at)
        self.chore = ChoreFactory(due_at=due_at, alarm_at=alarm_at, **kwargs)
        """:type: Chore"""
        db.session.commit()

        self.previous = dict(due_at=self.chore.due_at, alarm_at=self.chore.alarm_at)
        self.last_alarm = None
        """:type: Alarm"""
        self.assert_alarm_dates = assert_alarm_dates

    def get_alarm(self, index):
        """Get an alarm from the underlying chore.

        :rtype: Alarm
        """
        return self.chore.alarms[index]

    def assert_saved_alarm(self, expected_alarm_count, expected_action):
        """Assert an alarm was saved to the history."""
        self.assert_alarm_count(expected_alarm_count)

        self.last_alarm = self.get_alarm(expected_alarm_count - 1)
        """:type: Alarm"""
        assert self.last_alarm.action == expected_action

        if self.assert_alarm_dates:
            assert self.last_alarm.due_at == self.previous['due_at']
            assert self.last_alarm.alarm_at == self.previous['alarm_at']

    def assert_alarm_count(self, expected_alarm_count):
        """Assert the expected alarm count."""
        assert len(self.chore.alarms) == expected_alarm_count

    def assert_empty_dates(self):
        """Assert both dates are empty."""
        assert self.chore.due_at is None, 'Expected None, got {}'.format(
            arrow.get(self.chore.due_at).format(DATETIME_FORMAT))
        assert self.chore.alarm_at is None, 'Expected None, got {}'.format(
            arrow.get(self.chore.alarm_at).format(DATETIME_FORMAT))

    def assert_date(self, field_name, close_to_now=False, **kwargs):
        """Assert if the date field matches the timedelta.

        :param field_name: Name of the field: due_at or alarm_at.
        :param close_to_now: Assert both chore dates are close to the current time
            (since we cannot assert the exact time).
        :param kwargs: Arguments to the timedelta() function.
        """
        if close_to_now:
            expected = right_now() + timedelta(**kwargs)
            begin = expected - timedelta(seconds=self.NOW_PRECISION_SECONDS)
            end = expected + timedelta(seconds=self.NOW_PRECISION_SECONDS)
            value = getattr(self.chore, field_name)

            assert begin <= value <= end, 'Field {} with value {} should be between {} and {}'.format(
                field_name, value, arrow.get(begin).format(DATETIME_FORMAT), arrow.get(end).format(DATETIME_FORMAT)
            )
        else:
            expected = self.previous[field_name]
            if kwargs:
                expected += timedelta(**kwargs)
            actual = getattr(self.chore, field_name)
            assert actual == expected, 'Expected {} {}, got {}'.format(
                field_name, arrow.get(expected).format(DATETIME_FORMAT), arrow.get(actual).format(DATETIME_FORMAT))

        self.previous[field_name] = expected

    def assert_both_dates(self, close_to_now=False, **kwargs):
        """Assert if the due and alarm times match the timedelta."""
        self.assert_date('due_at', close_to_now, **kwargs)
        self.assert_date('alarm_at', close_to_now, **kwargs)


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


def test_active_inactive_future_chores(app):
    """Query active, inactive and future chores."""
    assert app

    ChoreFactory(due_at=YESTERDAY, alarm_end=YESTERDAY)  # Not active
    ChoreFactory(due_at=YESTERDAY, alarm_end=NEXT_WEEK)  # Active, with end
    ChoreFactory(due_at=YESTERDAY)  # Active, no end
    ChoreFactory(due_at=NEXT_WEEK)  # Not active, future
    db.session.commit()

    assert Chore.query_active().count() == 2
    assert Chore.query_inactive().count() == 2
    assert Chore.query_future().count() == 1

    after_next_week = NEXT_WEEK + timedelta(seconds=1)
    assert Chore.query_active(after_next_week).count() == 2
    assert Chore.query_inactive(after_next_week).count() == 2
    assert Chore.query_future(after_next_week).count() == 0


def test_one_time_only(app):
    """One time only chore."""
    fake = FakeChore(app)

    fake.chore.complete()
    fake.assert_saved_alarm(1, AlarmAction.COMPLETE)
    fake.assert_empty_dates()


def test_repetition_from_due_date(app):
    """Chore with repetition from due date."""
    fake = FakeChore(app, repetition='Daily')

    fake.chore.complete()
    fake.assert_saved_alarm(1, AlarmAction.COMPLETE)
    fake.assert_both_dates(days=1)

    fake.chore.complete()
    fake.assert_saved_alarm(2, AlarmAction.COMPLETE)
    fake.assert_both_dates(days=1)

    fake.chore.pause()
    fake.assert_alarm_count(2)
    fake.assert_empty_dates()


def test_repetition_from_completed(app):
    """Chore with repetition from completion date."""
    fake = FakeChore(app, repetition='Every 2 days', due_at=YESTERDAY, repeat_from_completed=True,
                     assert_alarm_dates=False)

    fake.chore.complete()
    fake.assert_saved_alarm(1, AlarmAction.COMPLETE)
    fake.assert_both_dates(close_to_now=True, days=2)

    fake.chore.complete()
    fake.assert_saved_alarm(2, AlarmAction.COMPLETE)
    fake.assert_both_dates(close_to_now=True, days=2)

    fake.chore.pause()
    fake.assert_alarm_count(2)
    fake.assert_empty_dates()


def test_snooze_from_original_due_date(app):
    """When you snooze a chore and then complete it later, the original date should get the repetition."""
    ten_oclock = TODAY.replace(hour=10, minute=0, second=0, microsecond=0)
    fake = FakeChore(app, repetition='Every 3 days', due_at=ten_oclock, assert_alarm_dates=False)

    # Snooze several times.
    for index, hours in enumerate([2, 1, 4]):
        fake.chore.snooze('{} hours'.format(hours))
        fake.assert_saved_alarm(index + 1, AlarmAction.SNOOZE)
        fake.assert_date('due_at')
        fake.assert_date('alarm_at', close_to_now=True, hours=hours)

    # Skip one occurrence.
    fake.chore.jump()
    fake.assert_saved_alarm(4, AlarmAction.JUMP)
    fake.assert_date('due_at', days=3)
    assert fake.chore.due_at == fake.chore.alarm_at

    # Snooze again several times.
    for index, minutes in enumerate([10, 15, 30, 10]):
        fake.chore.snooze('{} minutes'.format(minutes))
        fake.assert_saved_alarm(index + 5, AlarmAction.SNOOZE)
        fake.assert_date('due_at')
        fake.assert_date('alarm_at', close_to_now=True, minutes=minutes)

    # Finally complete the chore.
    fake.chore.complete()
    fake.assert_saved_alarm(9, AlarmAction.COMPLETE)
    fake.assert_date('due_at', days=3)
    assert fake.chore.due_at == fake.chore.alarm_at
