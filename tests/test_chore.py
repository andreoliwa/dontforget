# -*- coding: utf-8 -*-
# pylint: disable=invalid-name,no-member
"""Tests the chore model."""
from datetime import datetime, timedelta

from dontforget.cron import spawn_alarms
from dontforget.models import AlarmState, Chore
from tests.factories import ChoreFactory


def test_search_similar(db):
    """Search for similar chores."""
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


def test_create_alarms_for_active_chores(db):
    """Create alarms for active chores."""
    today = datetime.now()
    next_week = today + timedelta(days=7)
    yesterday = today - timedelta(days=1)

    veggie = ChoreFactory(title='Buy vegetables', alarm_start=yesterday, alarm_end=yesterday)
    coffee = ChoreFactory(title='Buy coffee', alarm_start=today, alarm_end=next_week)
    chocolate = ChoreFactory(title='Buy chocolate', alarm_start=today)
    db.session.commit()

    assert spawn_alarms(today) == 2
    db.session.commit()

    # No alarms for inactive chores, one alarm each for each active chore.
    assert len(veggie.alarms) == 0

    assert len(coffee.alarms) == 1
    alarm = coffee.alarms[0]
    assert alarm.next_at == today
    assert alarm.current_state == AlarmState.UNSEEN

    assert len(chocolate.alarms) == 1
    alarm = chocolate.alarms[0]
    assert alarm.next_at == today
    assert alarm.current_state == AlarmState.UNSEEN

    # Mark alarm as skipped, and spawn again.
    alarm.current_state = AlarmState.SKIPPED
    alarm.save()
    assert spawn_alarms(today) == 1
    db.session.commit()

    # There should be one new alarm for chocolate.
    assert len(veggie.alarms) == 0
    assert len(coffee.alarms) == 1
    assert len(chocolate.alarms) == 2
    assert chocolate.alarms[0].next_at == today
    assert chocolate.alarms[0].current_state == AlarmState.SKIPPED
    assert chocolate.alarms[1].next_at == today  # TODO + timedelta(days=1) # This will only work after repetition.
    assert chocolate.alarms[1].current_state == AlarmState.UNSEEN

    # Nothing changed, so no spawn for you.
    assert spawn_alarms(today) == 0
